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
- `use_autoprompt`: Enable Exa's autoprompt feature (default: True)
- `type`: Search type - "auto", "neural", or "keyword" (default: "auto")
- `include_domains`: List of domains to include
- `exclude_domains`: List of domains to exclude
- `start_published_date`: Filter results after this date (ISO format)
- `end_published_date`: Filter results before this date (ISO format)
- `category`: Search category filter

### ExaFindSimilar

Find similar pages using Exa's `/findSimilar` endpoint.

**Parameters:**
- `api_key`: Exa API key (default: from `EXA_API_KEY` env var)
- `num_results`: Number of results to return (default: 10)
- `include_domains`: List of domains to include
- `exclude_domains`: List of domains to exclude

### ExaContents

Fetch content for URLs using Exa's `/contents` endpoint.

**Parameters:**
- `api_key`: Exa API key (default: from `EXA_API_KEY` env var)
- `text`: Include full text content (default: True)
- `highlights`: Include highlighted snippets (default: False)
- `summary`: Include AI-generated summary (default: False)

## License

Apache-2.0
