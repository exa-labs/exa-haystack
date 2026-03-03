# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import Any, Literal

import requests
from haystack import component, default_from_dict, default_to_dict, logging
from haystack.dataclasses import Document
from haystack.utils import Secret, deserialize_secrets_inplace
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from haystack_integrations.components.websearch.exa.errors import ExaError

logger = logging.getLogger(__name__)

Category = Literal[
    "company",
    "research paper",
    "news",
    "pdf",
    "tweet",
    "personal site",
    "financial report",
    "people",
]

SearchType = Literal["auto", "fast", "deep"]

LivecrawlOption = Literal["always", "fallback", "never", "auto", "preferred"]


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
        type: SearchType = "auto",
        include_domains: list[str] | None = None,
        exclude_domains: list[str] | None = None,
        start_crawl_date: str | None = None,
        end_crawl_date: str | None = None,
        start_published_date: str | None = None,
        end_published_date: str | None = None,
        include_text: list[str] | None = None,
        exclude_text: list[str] | None = None,
        category: Category | None = None,
        flags: list[str] | None = None,
        moderation: bool | None = None,
        user_location: str | None = None,
        additional_queries: list[str] | None = None,
        text: bool | dict[str, Any] | None = None,
        highlights: bool | dict[str, Any] | None = None,
        summary: bool | dict[str, Any] | None = None,
        livecrawl: LivecrawlOption | None = None,
        livecrawl_timeout: int | None = None,
    ):
        self.api_key = api_key
        self.num_results = num_results
        self.use_autoprompt = use_autoprompt
        self.type = type
        self.include_domains = include_domains
        self.exclude_domains = exclude_domains
        self.start_crawl_date = start_crawl_date
        self.end_crawl_date = end_crawl_date
        self.start_published_date = start_published_date
        self.end_published_date = end_published_date
        self.include_text = include_text
        self.exclude_text = exclude_text
        self.category = category
        self.flags = flags
        self.moderation = moderation
        self.user_location = user_location
        self.additional_queries = additional_queries
        self.text = text
        self.highlights = highlights
        self.summary = summary
        self.livecrawl = livecrawl
        self.livecrawl_timeout = livecrawl_timeout

    def to_dict(self) -> dict[str, Any]:
        return default_to_dict(
            self,
            api_key=self.api_key.to_dict(),
            num_results=self.num_results,
            use_autoprompt=self.use_autoprompt,
            type=self.type,
            include_domains=self.include_domains,
            exclude_domains=self.exclude_domains,
            start_crawl_date=self.start_crawl_date,
            end_crawl_date=self.end_crawl_date,
            start_published_date=self.start_published_date,
            end_published_date=self.end_published_date,
            include_text=self.include_text,
            exclude_text=self.exclude_text,
            category=self.category,
            flags=self.flags,
            moderation=self.moderation,
            user_location=self.user_location,
            additional_queries=self.additional_queries,
            text=self.text,
            highlights=self.highlights,
            summary=self.summary,
            livecrawl=self.livecrawl,
            livecrawl_timeout=self.livecrawl_timeout,
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
        headers = {
            "x-api-key": self.api_key.resolve_value(),
            "Content-Type": "application/json",
            "x-exa-integration": "exa-haystack",
        }
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
        if self.start_crawl_date:
            payload["startCrawlDate"] = self.start_crawl_date
        if self.end_crawl_date:
            payload["endCrawlDate"] = self.end_crawl_date
        if self.start_published_date:
            payload["startPublishedDate"] = self.start_published_date
        if self.end_published_date:
            payload["endPublishedDate"] = self.end_published_date
        if self.include_text:
            payload["includeText"] = self.include_text
        if self.exclude_text:
            payload["excludeText"] = self.exclude_text
        if self.category:
            payload["category"] = self.category
        if self.flags:
            payload["flags"] = self.flags
        if self.moderation is not None:
            payload["moderation"] = self.moderation
        if self.user_location:
            payload["userLocation"] = self.user_location
        if self.additional_queries:
            payload["additionalQueries"] = self.additional_queries

        contents: dict[str, Any] = {}
        if self.text is not None:
            contents["text"] = self.text if isinstance(self.text, dict) else {}
        if self.highlights is not None:
            contents["highlights"] = self.highlights if isinstance(self.highlights, dict) else {}
        if self.summary is not None:
            contents["summary"] = self.summary if isinstance(self.summary, dict) else {}
        if self.livecrawl:
            contents["livecrawl"] = self.livecrawl
        if self.livecrawl_timeout:
            contents["livecrawlTimeout"] = self.livecrawl_timeout
        if contents:
            payload["contents"] = contents

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
            content = result.get("text", result.get("title", ""))
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
            if result.get("highlightScores"):
                meta["highlight_scores"] = result.get("highlightScores")
            if result.get("subpages"):
                meta["subpages"] = result.get("subpages")
            if result.get("extras"):
                meta["extras"] = result.get("extras")
            if result.get("entities"):
                meta["entities"] = result.get("entities")

            doc = Document(content=content, meta=meta)
            documents.append(doc)
            links.append(result.get("url", ""))

        logger.debug("ExaWebSearch returned {count} documents for query '{query}'", count=len(documents), query=query)
        return {"documents": documents, "links": links}
