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

LivecrawlOption = Literal["always", "fallback", "never", "auto", "preferred"]


@component
class ExaContents:
    """
    Fetch content for URLs using Exa's contents API.

    Usage:
    ```python
    from haystack_integrations.components.websearch.exa import ExaContents

    contents = ExaContents(text=True, highlights=True, summary=True)
    results = contents.run(urls=["https://example.com/article"])
    ```
    """

    def __init__(
        self,
        api_key: Secret = Secret.from_env_var("EXA_API_KEY"),
        text: bool | dict[str, Any] | None = True,
        highlights: bool | dict[str, Any] | None = None,
        summary: bool | dict[str, Any] | None = None,
        livecrawl: LivecrawlOption | None = None,
        livecrawl_timeout: int | None = None,
        filter_empty_results: bool | None = None,
        subpages: int | None = None,
        subpage_target: str | None = None,
        extras: dict[str, bool] | None = None,
        flags: list[str] | None = None,
    ):
        self.api_key = api_key
        self.text = text
        self.highlights = highlights
        self.summary = summary
        self.livecrawl = livecrawl
        self.livecrawl_timeout = livecrawl_timeout
        self.filter_empty_results = filter_empty_results
        self.subpages = subpages
        self.subpage_target = subpage_target
        self.extras = extras
        self.flags = flags

    def to_dict(self) -> dict[str, Any]:
        return default_to_dict(
            self,
            api_key=self.api_key.to_dict(),
            text=self.text,
            highlights=self.highlights,
            summary=self.summary,
            livecrawl=self.livecrawl,
            livecrawl_timeout=self.livecrawl_timeout,
            filter_empty_results=self.filter_empty_results,
            subpages=self.subpages,
            subpage_target=self.subpage_target,
            extras=self.extras,
            flags=self.flags,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExaContents":
        deserialize_secrets_inplace(data["init_parameters"], keys=["api_key"])
        return default_from_dict(cls, data)

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((requests.Timeout, requests.ConnectionError)),
    )
    def _make_request(self, headers: dict[str, Any], payload: dict[str, Any]) -> requests.Response:
        response = requests.post("https://api.exa.ai/contents", headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        return response

    @component.output_types(documents=list[Document])
    def run(self, urls: list[str]) -> dict[str, list[Document]]:
        headers = {
            "x-api-key": self.api_key.resolve_value(),
            "Content-Type": "application/json",
            "x-exa-integration": "exa-haystack",
        }
        payload: dict[str, Any] = {"ids": urls}

        if self.text is not None:
            payload["text"] = self.text if isinstance(self.text, dict) else self.text
        if self.highlights is not None:
            payload["highlights"] = self.highlights if isinstance(self.highlights, dict) else self.highlights
        if self.summary is not None:
            payload["summary"] = self.summary if isinstance(self.summary, dict) else self.summary
        if self.livecrawl:
            payload["livecrawl"] = self.livecrawl
        if self.livecrawl_timeout:
            payload["livecrawlTimeout"] = self.livecrawl_timeout
        if self.filter_empty_results is not None:
            payload["filterEmptyResults"] = self.filter_empty_results
        if self.subpages:
            payload["subpages"] = self.subpages
        if self.subpage_target:
            payload["subpageTarget"] = self.subpage_target
        if self.extras:
            payload["extras"] = self.extras
        if self.flags:
            payload["flags"] = self.flags

        try:
            response = self._make_request(headers, payload)
        except requests.Timeout as e:
            raise TimeoutError("Request to ExaContents timed out.") from e
        except requests.RequestException as e:
            raise ExaError(f"An error occurred while querying ExaContents: {e}") from e

        data = response.json()

        documents = []
        for result in data.get("results", []):
            content = result.get("text", "")
            highlights_list = result.get("highlights", [])
            if highlights_list and not content:
                content = " ... ".join(highlights_list)

            meta: dict[str, Any] = {
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "id": result.get("id"),
                "author": result.get("author"),
                "published_date": result.get("publishedDate"),
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

        logger.debug(
            "ExaContents returned {count} documents for {url_count} urls", count=len(documents), url_count=len(urls)
        )
        return {"documents": documents}
