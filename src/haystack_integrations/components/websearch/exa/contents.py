# SPDX-License-Identifier: Apache-2.0

from typing import Any

import requests
from haystack import component, default_from_dict, default_to_dict
from haystack.dataclasses import Document
from haystack.utils import Secret, deserialize_secrets_inplace


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

        response = requests.post("https://api.exa.ai/contents", headers=headers, json=payload, timeout=30)
        response.raise_for_status()
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

        return {"documents": documents}
