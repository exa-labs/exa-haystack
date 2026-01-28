# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import Any

import requests
from haystack import component, default_from_dict, default_to_dict, logging
from haystack.dataclasses import Document
from haystack.utils import Secret, deserialize_secrets_inplace
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from haystack_integrations.components.websearch.exa.errors import ExaError

logger = logging.getLogger(__name__)


@component
class ExaWebSearch:
    """
    Search the web using Exa's neural search API.

    Usage:
    ```python
    from haystack_integrations.components.websearch.exa import ExaWebSearch

    search = ExaWebSearch(num_results=5)
    results = search.run(query="latest AI research papers")
    ```
    """

    def __init__(
        self,
        api_key: Secret = Secret.from_env_var("EXA_API_KEY"),
        num_results: int = 10,
        use_autoprompt: bool = True,
        type: str = "auto",
        include_domains: list[str] | None = None,
        exclude_domains: list[str] | None = None,
        start_published_date: str | None = None,
        end_published_date: str | None = None,
        category: str | None = None,
    ):
        self.api_key = api_key
        self.num_results = num_results
        self.use_autoprompt = use_autoprompt
        self.type = type
        self.include_domains = include_domains
        self.exclude_domains = exclude_domains
        self.start_published_date = start_published_date
        self.end_published_date = end_published_date
        self.category = category

    def to_dict(self) -> dict[str, Any]:
        return default_to_dict(
            self,
            api_key=self.api_key.to_dict(),
            num_results=self.num_results,
            use_autoprompt=self.use_autoprompt,
            type=self.type,
            include_domains=self.include_domains,
            exclude_domains=self.exclude_domains,
            start_published_date=self.start_published_date,
            end_published_date=self.end_published_date,
            category=self.category,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExaWebSearch":
        deserialize_secrets_inplace(data["init_parameters"], keys=["api_key"])
        return default_from_dict(cls, data)

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((requests.Timeout, requests.ConnectionError)),
    )
    def _make_request(self, headers: dict[str, Any], payload: dict[str, Any]) -> requests.Response:
        response = requests.post("https://api.exa.ai/search", headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        return response

    @component.output_types(documents=list[Document], links=list[str])
    def run(self, query: str) -> dict[str, list[Document] | list[str]]:
        headers = {"x-api-key": self.api_key.resolve_value(), "Content-Type": "application/json"}
        payload: dict[str, Any] = {
            "query": query,
            "numResults": self.num_results,
            "useAutoprompt": self.use_autoprompt,
            "type": self.type,
        }
        if self.include_domains:
            payload["includeDomains"] = self.include_domains
        if self.exclude_domains:
            payload["excludeDomains"] = self.exclude_domains
        if self.start_published_date:
            payload["startPublishedDate"] = self.start_published_date
        if self.end_published_date:
            payload["endPublishedDate"] = self.end_published_date
        if self.category:
            payload["category"] = self.category

        try:
            response = self._make_request(headers, payload)
        except requests.Timeout as e:
            raise TimeoutError("Request to ExaWebSearch timed out.") from e
        except requests.RequestException as e:
            raise ExaError(f"An error occurred while querying ExaWebSearch: {e}") from e

        data = response.json()

        documents = []
        links = []
        for result in data.get("results", []):
            doc = Document(
                content=result.get("text", result.get("title", "")),
                meta={
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "score": result.get("score"),
                    "published_date": result.get("publishedDate"),
                    "author": result.get("author"),
                },
            )
            documents.append(doc)
            links.append(result.get("url", ""))

        logger.debug("ExaWebSearch returned {count} documents for query '{query}'", count=len(documents), query=query)
        return {"documents": documents, "links": links}
