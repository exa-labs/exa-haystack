# SPDX-License-Identifier: Apache-2.0

import os
from unittest.mock import MagicMock, patch

from haystack.utils import Secret

from haystack_integrations.components.websearch.exa import ExaContents, ExaFindSimilar, ExaWebSearch


class TestExaWebSearch:
    def test_init_default(self):
        with patch.dict(os.environ, {"EXA_API_KEY": "test-key"}):
            component = ExaWebSearch()
            assert component.num_results == 10
            assert component.use_autoprompt is True
            assert component.type == "auto"
            assert component.include_domains is None
            assert component.exclude_domains is None

    def test_init_custom(self):
        component = ExaWebSearch(
            api_key=Secret.from_token("custom-key"),
            num_results=5,
            use_autoprompt=False,
            type="neural",
            include_domains=["example.com"],
            exclude_domains=["spam.com"],
            start_published_date="2024-01-01",
            end_published_date="2024-12-31",
            category="news",
        )
        assert component.num_results == 5
        assert component.use_autoprompt is False
        assert component.type == "neural"
        assert component.include_domains == ["example.com"]
        assert component.exclude_domains == ["spam.com"]
        assert component.start_published_date == "2024-01-01"
        assert component.end_published_date == "2024-12-31"
        assert component.category == "news"

    def test_to_dict(self):
        with patch.dict(os.environ, {"EXA_API_KEY": "test-key"}):
            component = ExaWebSearch(
                num_results=5,
                use_autoprompt=False,
                type="keyword",
            )
            data = component.to_dict()
            assert data["type"] == "haystack_integrations.components.websearch.exa.search.ExaWebSearch"
            assert data["init_parameters"]["num_results"] == 5
            assert data["init_parameters"]["use_autoprompt"] is False
            assert data["init_parameters"]["type"] == "keyword"

    def test_from_dict(self):
        data = {
            "type": "haystack_integrations.components.websearch.exa.search.ExaWebSearch",
            "init_parameters": {
                "api_key": {"type": "env_var", "env_vars": ["EXA_API_KEY"], "strict": True},
                "num_results": 3,
                "use_autoprompt": True,
                "type": "auto",
                "include_domains": None,
                "exclude_domains": None,
                "start_published_date": None,
                "end_published_date": None,
                "category": None,
            },
        }
        component = ExaWebSearch.from_dict(data)
        assert component.num_results == 3
        assert component.use_autoprompt is True

    @patch("haystack_integrations.components.websearch.exa.search.requests.post")
    def test_run_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "title": "Test Article",
                    "url": "https://example.com/article",
                    "text": "This is the article content.",
                    "score": 0.95,
                    "publishedDate": "2024-01-15",
                    "author": "John Doe",
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        component = ExaWebSearch(api_key=Secret.from_token("test-key"))
        result = component.run(query="test query")

        assert len(result["documents"]) == 1
        assert result["documents"][0].content == "This is the article content."
        assert result["documents"][0].meta["title"] == "Test Article"
        assert result["documents"][0].meta["url"] == "https://example.com/article"
        assert result["documents"][0].meta["score"] == 0.95
        assert result["links"] == ["https://example.com/article"]

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[1]["json"]["query"] == "test query"
        assert call_args[1]["json"]["numResults"] == 10


class TestExaFindSimilar:
    def test_init_default(self):
        with patch.dict(os.environ, {"EXA_API_KEY": "test-key"}):
            component = ExaFindSimilar()
            assert component.num_results == 10
            assert component.include_domains is None

    def test_init_custom(self):
        component = ExaFindSimilar(
            api_key=Secret.from_token("custom-key"),
            num_results=5,
            include_domains=["example.com"],
            exclude_domains=["spam.com"],
        )
        assert component.num_results == 5
        assert component.include_domains == ["example.com"]
        assert component.exclude_domains == ["spam.com"]

    def test_to_dict(self):
        with patch.dict(os.environ, {"EXA_API_KEY": "test-key"}):
            component = ExaFindSimilar(num_results=5)
            data = component.to_dict()
            assert data["type"] == "haystack_integrations.components.websearch.exa.find_similar.ExaFindSimilar"
            assert data["init_parameters"]["num_results"] == 5

    def test_from_dict(self):
        data = {
            "type": "haystack_integrations.components.websearch.exa.find_similar.ExaFindSimilar",
            "init_parameters": {
                "api_key": {"type": "env_var", "env_vars": ["EXA_API_KEY"], "strict": True},
                "num_results": 3,
                "include_domains": None,
                "exclude_domains": None,
            },
        }
        component = ExaFindSimilar.from_dict(data)
        assert component.num_results == 3

    @patch("haystack_integrations.components.websearch.exa.find_similar.requests.post")
    def test_run_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "title": "Similar Article",
                    "url": "https://example.com/similar",
                    "text": "Similar content here.",
                    "score": 0.85,
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        component = ExaFindSimilar(api_key=Secret.from_token("test-key"))
        result = component.run(url="https://example.com/original")

        assert len(result["documents"]) == 1
        assert result["documents"][0].content == "Similar content here."
        assert result["documents"][0].meta["url"] == "https://example.com/similar"
        assert result["links"] == ["https://example.com/similar"]

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[1]["json"]["url"] == "https://example.com/original"


class TestExaContents:
    def test_init_default(self):
        with patch.dict(os.environ, {"EXA_API_KEY": "test-key"}):
            component = ExaContents()
            assert component.text is True
            assert component.highlights is False
            assert component.summary is False

    def test_init_custom(self):
        component = ExaContents(
            api_key=Secret.from_token("custom-key"),
            text=True,
            highlights=True,
            summary=True,
        )
        assert component.text is True
        assert component.highlights is True
        assert component.summary is True

    def test_to_dict(self):
        with patch.dict(os.environ, {"EXA_API_KEY": "test-key"}):
            component = ExaContents(text=True, highlights=True, summary=False)
            data = component.to_dict()
            assert data["type"] == "haystack_integrations.components.websearch.exa.contents.ExaContents"
            assert data["init_parameters"]["text"] is True
            assert data["init_parameters"]["highlights"] is True
            assert data["init_parameters"]["summary"] is False

    def test_from_dict(self):
        data = {
            "type": "haystack_integrations.components.websearch.exa.contents.ExaContents",
            "init_parameters": {
                "api_key": {"type": "env_var", "env_vars": ["EXA_API_KEY"], "strict": True},
                "text": True,
                "highlights": False,
                "summary": True,
            },
        }
        component = ExaContents.from_dict(data)
        assert component.text is True
        assert component.highlights is False
        assert component.summary is True

    @patch("haystack_integrations.components.websearch.exa.contents.requests.post")
    def test_run_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "title": "Full Article",
                    "url": "https://example.com/article",
                    "text": "Full article content here.",
                    "summary": "A brief summary.",
                    "highlights": ["Important point 1", "Important point 2"],
                    "author": "Jane Doe",
                    "publishedDate": "2024-02-01",
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        component = ExaContents(api_key=Secret.from_token("test-key"), text=True, highlights=True, summary=True)
        result = component.run(urls=["https://example.com/article"])

        assert len(result["documents"]) == 1
        assert result["documents"][0].content == "Full article content here."
        assert result["documents"][0].meta["title"] == "Full Article"
        assert result["documents"][0].meta["summary"] == "A brief summary."
        assert result["documents"][0].meta["highlights"] == ["Important point 1", "Important point 2"]

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[1]["json"]["ids"] == ["https://example.com/article"]
        assert call_args[1]["json"]["text"] is True
        assert call_args[1]["json"]["highlights"] is True
        assert call_args[1]["json"]["summary"] is True

    @patch("haystack_integrations.components.websearch.exa.contents.requests.post")
    def test_run_highlights_only(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "title": "Article",
                    "url": "https://example.com/article",
                    "highlights": ["Highlight 1", "Highlight 2"],
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        component = ExaContents(api_key=Secret.from_token("test-key"), text=False, highlights=True)
        result = component.run(urls=["https://example.com/article"])

        assert len(result["documents"]) == 1
        assert result["documents"][0].content == "Highlight 1 ... Highlight 2"
