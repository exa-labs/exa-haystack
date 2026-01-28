# SPDX-License-Identifier: Apache-2.0

"""
Basic usage examples for the Exa-Haystack integration.

Make sure to set your EXA_API_KEY environment variable before running:
    export EXA_API_KEY="your-api-key"
"""

from haystack_integrations.components.websearch.exa import ExaContents, ExaFindSimilar, ExaWebSearch


def example_web_search():
    """Basic web search example."""
    print("=== ExaWebSearch Example ===\n")

    search = ExaWebSearch(num_results=3, use_autoprompt=True, type="auto")
    results = search.run(query="latest developments in quantum computing")

    for doc in results["documents"]:
        print(f"Title: {doc.meta['title']}")
        print(f"URL: {doc.meta['url']}")
        print(f"Score: {doc.meta.get('score', 'N/A')}")
        print(f"Content: {doc.content[:200]}..." if len(doc.content) > 200 else f"Content: {doc.content}")
        print()


def example_find_similar():
    """Find similar pages example."""
    print("=== ExaFindSimilar Example ===\n")

    find_similar = ExaFindSimilar(num_results=3)
    results = find_similar.run(url="https://www.nature.com/articles/s41586-023-06096-3")

    for doc in results["documents"]:
        print(f"Title: {doc.meta['title']}")
        print(f"URL: {doc.meta['url']}")
        print()


def example_contents():
    """Fetch full content example."""
    print("=== ExaContents Example ===\n")

    contents = ExaContents(text=True, highlights=True, summary=True)
    results = contents.run(urls=["https://www.nature.com/articles/s41586-023-06096-3"])

    for doc in results["documents"]:
        print(f"Title: {doc.meta['title']}")
        print(f"Summary: {doc.meta.get('summary', 'N/A')}")
        print(f"Content length: {len(doc.content)} characters")
        print()


def example_domain_filtering():
    """Search with domain filtering."""
    print("=== Domain Filtering Example ===\n")

    search = ExaWebSearch(
        num_results=3,
        include_domains=["arxiv.org", "nature.com", "science.org"],
        exclude_domains=["reddit.com"],
    )
    results = search.run(query="machine learning research papers")

    for doc in results["documents"]:
        print(f"Title: {doc.meta['title']}")
        print(f"URL: {doc.meta['url']}")
        print()


def example_date_filtering():
    """Search with date filtering."""
    print("=== Date Filtering Example ===\n")

    search = ExaWebSearch(
        num_results=3,
        start_published_date="2024-01-01",
        end_published_date="2024-12-31",
    )
    results = search.run(query="AI breakthroughs 2024")

    for doc in results["documents"]:
        print(f"Title: {doc.meta['title']}")
        print(f"Published: {doc.meta.get('published_date', 'N/A')}")
        print(f"URL: {doc.meta['url']}")
        print()


def example_pipeline():
    """Using Exa in a Haystack pipeline."""
    print("=== Pipeline Example ===\n")

    from haystack import Pipeline
    from haystack.components.builders import PromptBuilder

    template = """
Based on the following search results, provide a brief summary.

Search Results:
{% for doc in documents %}
Title: {{ doc.meta.title }}
Content: {{ doc.content[:500] }}
---
{% endfor %}

Summary:
"""

    pipe = Pipeline()
    pipe.add_component("search", ExaWebSearch(num_results=3))
    pipe.add_component("prompt", PromptBuilder(template=template))
    pipe.connect("search.documents", "prompt.documents")

    result = pipe.run({"search": {"query": "What is retrieval augmented generation?"}})

    print("Generated prompt:")
    print(result["prompt"]["prompt"][:1000])
    print("...")


if __name__ == "__main__":
    import sys

    examples = {
        "search": example_web_search,
        "similar": example_find_similar,
        "contents": example_contents,
        "domains": example_domain_filtering,
        "dates": example_date_filtering,
        "pipeline": example_pipeline,
    }

    if len(sys.argv) > 1 and sys.argv[1] in examples:
        examples[sys.argv[1]]()
    else:
        print("Available examples: search, similar, contents, domains, dates, pipeline")
        print("Usage: python basic_usage.py <example_name>")
        print("\nRunning all examples...\n")
        for name, func in examples.items():
            try:
                func()
            except Exception as e:
                print(f"Example '{name}' failed: {e}\n")
