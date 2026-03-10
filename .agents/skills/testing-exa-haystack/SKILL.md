# Testing exa-haystack Integration

## Overview
The exa-haystack package provides Haystack components that wrap the Exa API. Testing involves running the components against the live Exa API to verify they correctly construct payloads and parse responses.

## Devin Secrets Needed
- `EXA_API_KEY` — Exa API key, set as env var

## Setup
1. Activate the venv: `source .venv/bin/activate`
2. Ensure the package is installed in editable mode: `pip install -e .`
3. Set `EXA_API_KEY` in environment

## Components and How to Test

### ExaWebSearch
- Import: `from haystack_integrations.components.websearch.exa import ExaWebSearch`
- Instantiation: `ExaWebSearch(num_results=3, type="auto", text=True)`
- Run: `result = search.run(query="...")`
- Returns: `{"documents": [...], "links": [...], "deep_output": None | dict}`
- Key params to test: `type` (auto/instant/fast/deep/deep-reasoning/deep-max/neural), `category` (company/research paper/news/pdf/tweet/personal site/financial report/people), `max_age_hours`, `output_schema`
- `deep_output` is only populated when using deep/deep-reasoning types with `output_schema`

### ExaFindSimilar
- Import: `from haystack_integrations.components.websearch.exa import ExaFindSimilar`
- Run: `result = find_similar.run(url="https://example.com")`
- Returns: `{"documents": [...], "links": [...]}`

### ExaContents
- Import: `from haystack_integrations.components.websearch.exa import ExaContents`
- Instantiation: `ExaContents(text=True, max_age_hours=0)`
- Run: `result = contents.run(urls=["https://..."])`
- Returns: `{"documents": [...], "statuses": [...]}`
- `statuses` contains per-URL status/error info from the API
- `max_age_hours=0` forces livecrawl; useful for testing freshness

### ExaAnswer
- Import: `from haystack_integrations.components.websearch.exa import ExaAnswer`
- Run: `result = answer.run(query="...")`
- Returns: `{"answer": "...", "citations": [...]}`
- Can take `output_schema` for structured JSON answers
- Timeout is 120s (answers can be slow)

### ExaStreamAnswer
- Import: `from haystack_integrations.components.websearch.exa import ExaStreamAnswer`
- Returns a generator for `stream` — must iterate to consume
- Citations are populated during iteration

## Testing Tips
- Write a Python script that instantiates each component and calls `.run()`. Don't use the browser for this.
- All components use `requests.post` to `api.exa.ai` endpoints with `x-exa-integration: exa-haystack` header
- The `type="instant"` search is fastest (<150ms) — good for quick smoke tests
- To verify a parameter was removed, try passing it and assert `TypeError` is raised
- Unit tests are in `tests/test_exa.py` — run with `pytest tests -v`
- Lint with `ruff check src/ tests/ examples/`
- CI runs tests on Python 3.9, 3.10, 3.11, 3.12

## Common Issues
- Python 3.9 compatibility: `@component.output_types()` decorator evaluates type hints at runtime. Use `typing.List`, `typing.Dict`, `typing.Optional` in decorator args instead of `list | None` syntax. The rest of the file can use modern syntax via `from __future__ import annotations`.
- `max_age_hours` goes inside `contents` dict in the payload for search/findSimilar, but top-level for the `/contents` endpoint
- `livecrawl` is deprecated but still supported — no runtime warning emitted
