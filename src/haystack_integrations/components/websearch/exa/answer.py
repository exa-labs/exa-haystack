# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import Any, Generator, Literal

import requests
from haystack import component, default_from_dict, default_to_dict, logging
from haystack.dataclasses import Document
from haystack.utils import Secret, deserialize_secrets_inplace
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from haystack_integrations.components.websearch.exa.errors import ExaError

logger = logging.getLogger(__name__)

AnswerModel = Literal["exa", "exa-pro"]


@component
class ExaAnswer:
    """
    Generate answers with citations using Exa's answer API.

    Usage:
    ```python
    from haystack_integrations.components.websearch.exa import ExaAnswer

    answer = ExaAnswer(model="exa")
    results = answer.run(query="What are the latest developments in AI?")
    ```
    """

    def __init__(
        self,
        api_key: Secret = Secret.from_env_var("EXA_API_KEY"),
        model: AnswerModel = "exa",
        text: bool | dict[str, Any] | None = True,
        system_prompt: str | None = None,
        user_location: str | None = None,
        output_schema: dict[str, Any] | None = None,
    ):
        self.api_key = api_key
        self.model = model
        self.text = text
        self.system_prompt = system_prompt
        self.user_location = user_location
        self.output_schema = output_schema

    def to_dict(self) -> dict[str, Any]:
        return default_to_dict(
            self,
            api_key=self.api_key.to_dict(),
            model=self.model,
            text=self.text,
            system_prompt=self.system_prompt,
            user_location=self.user_location,
            output_schema=self.output_schema,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExaAnswer":
        deserialize_secrets_inplace(data["init_parameters"], keys=["api_key"])
        return default_from_dict(cls, data)

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((requests.Timeout, requests.ConnectionError)),
    )
    def _make_request(self, headers: dict[str, Any], payload: dict[str, Any]) -> requests.Response:
        response = requests.post("https://api.exa.ai/answer", headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        return response

    @component.output_types(answer=str, citations=list[Document])
    def run(self, query: str) -> dict[str, str | list[Document]]:
        headers = {
            "x-api-key": self.api_key.resolve_value(),
            "Content-Type": "application/json",
            "x-exa-integration": "exa-haystack",
        }
        payload: dict[str, Any] = {
            "query": query,
            "model": self.model,
        }
        if self.text is not None:
            payload["text"] = self.text if isinstance(self.text, dict) else self.text
        if self.system_prompt:
            payload["systemPrompt"] = self.system_prompt
        if self.user_location:
            payload["userLocation"] = self.user_location
        if self.output_schema:
            payload["outputSchema"] = self.output_schema

        try:
            response = self._make_request(headers, payload)
        except requests.Timeout as e:
            raise TimeoutError("Request to ExaAnswer timed out.") from e
        except requests.RequestException as e:
            raise ExaError(f"An error occurred while querying ExaAnswer: {e}") from e

        data = response.json()

        answer_text = data.get("answer", "")
        citations = []
        for result in data.get("citations", []):
            meta: dict[str, Any] = {
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "id": result.get("id"),
                "score": result.get("score"),
                "published_date": result.get("publishedDate"),
                "author": result.get("author"),
                "image": result.get("image"),
                "favicon": result.get("favicon"),
            }
            if result.get("summary"):
                meta["summary"] = result.get("summary")
            if result.get("highlights"):
                meta["highlights"] = result.get("highlights")

            doc = Document(content=result.get("text", result.get("title", "")), meta=meta)
            citations.append(doc)

        logger.debug(
            "ExaAnswer returned answer with {count} citations for query '{query}'", count=len(citations), query=query
        )
        return {"answer": answer_text, "citations": citations}


@component
class ExaStreamAnswer:
    """
    Generate streaming answers with citations using Exa's answer API.

    Usage:
    ```python
    from haystack_integrations.components.websearch.exa import ExaStreamAnswer

    stream_answer = ExaStreamAnswer(model="exa")
    for chunk in stream_answer.run(query="What are the latest developments in AI?")["stream"]:
        print(chunk, end="", flush=True)
    ```
    """

    def __init__(
        self,
        api_key: Secret = Secret.from_env_var("EXA_API_KEY"),
        model: AnswerModel = "exa",
        text: bool | dict[str, Any] | None = True,
        system_prompt: str | None = None,
        user_location: str | None = None,
        output_schema: dict[str, Any] | None = None,
    ):
        self.api_key = api_key
        self.model = model
        self.text = text
        self.system_prompt = system_prompt
        self.user_location = user_location
        self.output_schema = output_schema

    def to_dict(self) -> dict[str, Any]:
        return default_to_dict(
            self,
            api_key=self.api_key.to_dict(),
            model=self.model,
            text=self.text,
            system_prompt=self.system_prompt,
            user_location=self.user_location,
            output_schema=self.output_schema,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExaStreamAnswer":
        deserialize_secrets_inplace(data["init_parameters"], keys=["api_key"])
        return default_from_dict(cls, data)

    @component.output_types(stream=Generator[str, None, None], citations=list[Document])
    def run(self, query: str) -> dict[str, Generator[str, None, None] | list[Document]]:
        headers = {
            "x-api-key": self.api_key.resolve_value(),
            "Content-Type": "application/json",
            "x-exa-integration": "exa-haystack",
        }
        payload: dict[str, Any] = {
            "query": query,
            "model": self.model,
            "stream": True,
        }
        if self.text is not None:
            payload["text"] = self.text if isinstance(self.text, dict) else self.text
        if self.system_prompt:
            payload["systemPrompt"] = self.system_prompt
        if self.user_location:
            payload["userLocation"] = self.user_location
        if self.output_schema:
            payload["outputSchema"] = self.output_schema

        try:
            response = requests.post(
                "https://api.exa.ai/answer",
                headers=headers,
                json=payload,
                timeout=120,
                stream=True,
            )
            response.raise_for_status()
        except requests.Timeout as e:
            raise TimeoutError("Request to ExaStreamAnswer timed out.") from e
        except requests.RequestException as e:
            raise ExaError(f"An error occurred while querying ExaStreamAnswer: {e}") from e

        citations: list[Document] = []

        def stream_generator() -> Generator[str, None, None]:
            import json as json_module

            for line in response.iter_lines():
                if line:
                    line_str = line.decode("utf-8")
                    if line_str.startswith("data: "):
                        data_str = line_str[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json_module.loads(data_str)
                            if "text" in data:
                                yield data["text"]
                            if "citations" in data:
                                for result in data["citations"]:
                                    meta: dict[str, Any] = {
                                        "title": result.get("title", ""),
                                        "url": result.get("url", ""),
                                        "id": result.get("id"),
                                        "score": result.get("score"),
                                        "published_date": result.get("publishedDate"),
                                        "author": result.get("author"),
                                    }
                                    doc = Document(content=result.get("text", result.get("title", "")), meta=meta)
                                    citations.append(doc)
                        except json_module.JSONDecodeError:
                            continue

        logger.debug("ExaStreamAnswer started streaming for query '{query}'", query=query)
        return {"stream": stream_generator(), "citations": citations}
