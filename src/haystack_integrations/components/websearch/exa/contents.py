# SPDX-License-Identifier: Apache-2.0

from typing import Any

import requests
from haystack import component, default_from_dict, default_to_dict, logging
from haystack.dataclasses import Document
from haystack.utils import Secret, deserialize_secrets_inplace
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from haystack_integrations.components.websearch.exa.errors import ExaError

logger = logging.getLogger(__name__)


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
        text: bool = True,
        highlights: bool = False,
        summary: bool = False,
    ):
        self.api_key = api_key
        self.text = text
        self.highlights = highlights
        self.summary = summary

    def to_dict(self) -> dict[str, Any]:
        return default_to_dict(
            self,
            api_key=self.api_key.to_dict(),
            text=self.text,
            highlights=self.highlights,
            summary=self.summary,
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
    def _make_request(self, headers: dict[str, str], payload: dict[str, Any]) -> requests.Response:
        response = requests.post("https://api.exa.ai/contents", headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        return response

    @component.output_types(documents=list[Document])
    def run(self, urls: list[str]) -> dict[str, list[Document]]:
        headers = {"x-api-key": self.api_key.resolve_value(), "Content-Type": "application/json"}
        payload: dict[str, Any] = {"ids": urls}
        if self.text:
            payload["text"] = True
        if self.highlights:
            payload["highlights"] = True
        if self.summary:
            payload["summary"] = True

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
                "author": result.get("author"),
                "published_date": result.get("publishedDate"),
            }
            if result.get("summary"):
                meta["summary"] = result.get("summary")
            if result.get("highlights"):
                meta["highlights"] = result.get("highlights")

            doc = Document(content=content, meta=meta)
            documents.append(doc)

        logger.debug("ExaContents returned {count} documents for {url_count} urls", count=len(documents), url_count=len(urls))
        return {"documents": documents}
