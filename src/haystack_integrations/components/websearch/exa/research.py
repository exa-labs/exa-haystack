# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import time
from typing import Any, Literal

import requests
from haystack import component, default_from_dict, default_to_dict, logging
from haystack.dataclasses import Document
from haystack.utils import Secret, deserialize_secrets_inplace
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from haystack_integrations.components.websearch.exa.errors import ExaError

logger = logging.getLogger(__name__)

ResearchModel = Literal["exa-research-fast", "exa-research", "exa-research-pro"]
ResearchStatus = Literal["pending", "running", "completed", "canceled", "failed"]


@component
class ExaResearch:
    """
    Conduct deep research using Exa's research API.

    Usage:
    ```python
    from haystack_integrations.components.websearch.exa import ExaResearch

    research = ExaResearch(model="exa-research")
    results = research.run(instructions="Research the latest developments in quantum computing")
    ```
    """

    def __init__(
        self,
        api_key: Secret = Secret.from_env_var("EXA_API_KEY"),
        model: ResearchModel = "exa-research",
        output_schema: dict[str, Any] | None = None,
        poll_interval: int = 5,
        max_wait_time: int = 600,
    ):
        self.api_key = api_key
        self.model = model
        self.output_schema = output_schema
        self.poll_interval = poll_interval
        self.max_wait_time = max_wait_time

    def to_dict(self) -> dict[str, Any]:
        return default_to_dict(
            self,
            api_key=self.api_key.to_dict(),
            model=self.model,
            output_schema=self.output_schema,
            poll_interval=self.poll_interval,
            max_wait_time=self.max_wait_time,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExaResearch":
        deserialize_secrets_inplace(data["init_parameters"], keys=["api_key"])
        return default_from_dict(cls, data)

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((requests.Timeout, requests.ConnectionError)),
    )
    def _create_research(self, headers: dict[str, Any], payload: dict[str, Any]) -> requests.Response:
        response = requests.post("https://api.exa.ai/research/v1", headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        return response

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((requests.Timeout, requests.ConnectionError)),
    )
    def _get_research(self, headers: dict[str, Any], research_id: str) -> requests.Response:
        response = requests.get(f"https://api.exa.ai/research/v1/{research_id}", headers=headers, timeout=30)
        response.raise_for_status()
        return response

    @component.output_types(report=str, sources=list[Document], status=str, events=list[dict[str, Any]])
    def run(self, instructions: str) -> dict[str, str | list[Document] | list[dict[str, Any]]]:
        headers = {
            "x-api-key": self.api_key.resolve_value(),
            "Content-Type": "application/json",
            "x-exa-integration": "exa-haystack",
        }
        payload: dict[str, Any] = {
            "instructions": instructions,
            "model": self.model,
        }
        if self.output_schema:
            payload["outputSchema"] = self.output_schema

        try:
            response = self._create_research(headers, payload)
        except requests.Timeout as e:
            raise TimeoutError("Request to create ExaResearch timed out.") from e
        except requests.RequestException as e:
            raise ExaError(f"An error occurred while creating ExaResearch: {e}") from e

        data = response.json()
        research_id = data.get("researchId")
        if not research_id:
            raise ExaError("No research ID returned from API")

        logger.debug("ExaResearch created with id '{research_id}'", research_id=research_id)

        start_time = time.time()
        while True:
            elapsed = time.time() - start_time
            if elapsed > self.max_wait_time:
                raise TimeoutError(f"ExaResearch timed out after {self.max_wait_time} seconds")

            try:
                response = self._get_research(headers, research_id)
            except requests.Timeout as e:
                raise TimeoutError("Request to get ExaResearch status timed out.") from e
            except requests.RequestException as e:
                raise ExaError(f"An error occurred while getting ExaResearch status: {e}") from e

            data = response.json()
            status = data.get("status", "unknown")

            if status == "completed":
                break
            elif status in ("failed", "canceled"):
                error_msg = data.get("error", "Unknown error")
                raise ExaError(f"ExaResearch {status}: {error_msg}")

            logger.debug(
                "ExaResearch status: {status}, waiting {interval}s", status=status, interval=self.poll_interval
            )
            time.sleep(self.poll_interval)

        output_data = data.get("output", {})
        report = output_data.get("content", "") if isinstance(output_data, dict) else str(output_data)
        events = data.get("events", [])

        sources: list[Document] = []
        for event in events:
            if event.get("eventType") in ("task-operation", "plan-operation"):
                op = event.get("data", {})
                if op.get("type") == "search" and "results" in op:
                    for result in op["results"]:
                        meta: dict[str, Any] = {
                            "title": result.get("title", ""),
                            "url": result.get("url", ""),
                        }
                        doc = Document(content=result.get("url", ""), meta=meta)
                        sources.append(doc)

        logger.debug("ExaResearch completed with {source_count} sources", source_count=len(sources))
        return {"report": report, "sources": sources, "status": status, "events": events}
