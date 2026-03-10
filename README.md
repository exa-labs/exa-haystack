# exa-haystack

[![PyPI version](https://badge.fury.io/py/exa-haystack.svg)](https://badge.fury.io/py/exa-haystack)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

Haystack integration for [Exa](https://exa.ai) - the search engine designed for AI.

## Installation

```bash
pip install exa-haystack
```

## Usage

### ExaWebSearch

Search the web using Exa's neural search:

```python
from haystack_integrations.components.websearch.exa import ExaWebSearch

search = ExaWebSearch(num_results=5)
results = search.run(query="latest developments in quantum computing")

for doc in results["documents"]:
    print(f"Title: {doc.meta['title']}")
    print(f"URL: {doc.meta['url']}")
    print(f"Content: {doc.content[:200]}...")
    print()
```

### ExaFindSimilar

Find pages similar to a given URL:

```python
from haystack_integrations.components.websearch.exa import ExaFindSimilar

find_similar = ExaFindSimilar(num_results=5)
results = find_similar.run(url="https://example.com/article")

for doc in results["documents"]:
    print(f"Similar: {doc.meta['title']} - {doc.meta['url']}")
```

### ExaContents

Fetch full content for URLs:

```python
from haystack_integrations.components.websearch.exa import ExaContents

contents = ExaContents(text=True, highlights=True, summary=True)
results = contents.run(urls=["https://example.com/article1", "https://example.com/article2"])

for doc in results["documents"]:
    print(f"Title: {doc.meta['title']}")
    print(f"Summary: {doc.meta.get('summary', 'N/A')}")
    print(f"Content: {doc.content[:500]}...")
```

### Using in a Pipeline

```python
from haystack import Pipeline
from haystack.components.builders import PromptBuilder
from haystack.components.generators import OpenAIGenerator
from haystack_integrations.components.websearch.exa import ExaWebSearch

template = """
Based on the following search results, answer the question.

Search Results:
{% for doc in documents %}
Title: {{ doc.meta.title }}
Content: {{ doc.content }}
---
{% endfor %}

Question: {{ query }}
Answer:
"""

pipe = Pipeline()
pipe.add_component("search", ExaWebSearch(num_results=3))
pipe.add_component("prompt", PromptBuilder(template=template))
pipe.add_component("llm", OpenAIGenerator())

pipe.connect("search.documents", "prompt.documents")
pipe.connect("prompt", "llm")

result = pipe.run({
    "search": {"query": "What is retrieval augmented generation?"},
    "prompt": {"query": "What is retrieval augmented generation?"}
})

print(result["llm"]["replies"][0])
```

## Configuration

Set your Exa API key as an environment variable:

```bash
export EXA_API_KEY="your-api-key"
```

Or pass it directly:

```python
from haystack.utils import Secret
from haystack_integrations.components.websearch.exa import ExaWebSearch

search = ExaWebSearch(api_key=Secret.from_token("your-api-key"))
```

## Components

### ExaWebSearch

Main search component using Exa's `/search` endpoint.

**Parameters:**
- `api_key`: Exa API key (default: from `EXA_API_KEY` env var)
- `num_results`: Number of results to return (default: 10)
- `type`: Search type — `"auto"`, `"neural"`, `"fast"`, `"deep"`, `"deep-reasoning"`, `"deep-max"`, `"instant"` (default: `"auto"`)
- `include_domains` / `exclude_domains`: Domain filters
- `start_published_date` / `end_published_date`: Date range filters (ISO format)
- `category`: Search category filter (`"company"`, `"research paper"`, `"news"`, `"pdf"`, `"tweet"`, `"personal site"`, `"financial report"`, `"people"`)
- `additional_queries`: Extra queries for deep search
- `output_schema`: JSON schema for structured deep search output (returns `deep_output` and `deep_grounding` in document metadata)
- `max_age_hours`: Content freshness control (`0` = always livecrawl, `-1` = cache only, positive = max cache age in hours)
- `livecrawl`: Legacy freshness option (deprecated, use `max_age_hours`)
- `text` / `highlights` / `summary`: Content options (bool or dict with sub-options)

### ExaFindSimilar

Find similar pages using Exa's `/findSimilar` endpoint.

**Parameters:**
- `api_key`: Exa API key (default: from `EXA_API_KEY` env var)
- `num_results`: Number of results to return (default: 10)
- `include_domains` / `exclude_domains`: Domain filters
- `exclude_source_domain`: Exclude the source URL's domain from results
- `category`: Search category filter
- `max_age_hours`: Content freshness control
- `livecrawl`: Legacy freshness option (deprecated, use `max_age_hours`)
- `text` / `highlights` / `summary`: Content options

### ExaContents

Fetch content for URLs using Exa's `/contents` endpoint.

**Parameters:**
- `api_key`: Exa API key (default: from `EXA_API_KEY` env var)
- `text`: Include full text content (default: True)
- `highlights`: Include highlighted snippets
- `summary`: Include AI-generated summary
- `max_age_hours`: Content freshness control
- `livecrawl`: Legacy freshness option (deprecated, use `max_age_hours`)
- `subpages` / `subpage_target`: Crawl linked subpages
- `extras` / `flags`: Additional extraction options

**Outputs:** `documents` (list of Documents) and `statuses` (per-URL status/error info)

### ExaAnswer

Generate AI-powered answers with citations using Exa's `/answer` endpoint.

**Parameters:**
- `api_key`: Exa API key (default: from `EXA_API_KEY` env var)
- `model`: `"exa"` or `"exa-pro"` (default: `"exa"`)
- `system_prompt`: Custom system prompt
- `output_schema`: JSON schema for structured answer output

### ExaStreamAnswer

Streaming variant of ExaAnswer — yields answer chunks via SSE.

### ExaResearch

Conduct deep research using Exa's `/research/v1` endpoint.

**Parameters:**
- `api_key`: Exa API key (default: from `EXA_API_KEY` env var)
- `model`: `"exa-research-fast"`, `"exa-research"`, or `"exa-research-pro"` (default: `"exa-research"`)
- `output_schema`: JSON schema for structured research output
- `poll_interval` / `max_wait_time`: Polling configuration

## License

Apache-2.0
