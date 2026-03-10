# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-03-10

### Added

- `output_schema` parameter on `ExaWebSearch` for structured deep search output (returned as `deep_output` component output)
- `output_schema` parameter on `ExaAnswer` and `ExaStreamAnswer` for structured answer output
- `max_age_hours` parameter on `ExaWebSearch`, `ExaFindSimilar`, and `ExaContents` for content freshness control
- `instant`, `deep-reasoning`, and `deep-max` search types on `ExaWebSearch`
- `neural` search type exposed in `SearchType` literal
- `statuses` output on `ExaContents` with per-URL status/error information
- Deep search synthesized output returned as `deep_output` component output (raw API output dict)

### Removed

- `use_autoprompt` parameter from `ExaWebSearch` (removed from Exa API)

### Deprecated

- `livecrawl` parameter — use `max_age_hours` instead (`0` = always livecrawl, `-1` = cache only)

## [1.0.0] - 2026-01-28

### Added

- `ExaWebSearch` component for Exa's `/search` endpoint with full parameter support
  - Search types: auto, neural, keyword
  - Date filtering: published date and crawl date ranges
  - Text filtering: include/exclude text patterns
  - Domain filtering: include/exclude domains
  - Category filtering: news, research paper, company, etc.
  - Content options: text, highlights, summary with livecrawl support
  - Advanced options: moderation, user_location, additional_queries

- `ExaFindSimilar` component for Exa's `/findSimilar` endpoint
  - Find pages similar to a given URL
  - All filtering options from ExaWebSearch
  - Additional exclude_source_domain option

- `ExaContents` component for Exa's `/contents` endpoint
  - Fetch full content for URLs
  - Livecrawl support with configurable timeout
  - Subpage crawling support
  - Extras: links, image_links

- `ExaAnswer` component for Exa's `/answer` endpoint
  - Generate answers with citations
  - Model selection: exa, exa-pro
  - System prompt customization

- `ExaStreamAnswer` component for streaming answers
  - Server-sent events (SSE) streaming support
  - Real-time answer generation

- `ExaResearch` component for Exa's `/research` endpoint
  - Deep research with automatic polling
  - Model selection: exa-research-fast, exa-research, exa-research-pro
  - Structured output schema support

- Custom `ExaError` exception class for error handling
- Retry logic with exponential backoff for transient failures
- Debug logging for all components
- Comprehensive test suite with 26 unit tests
- GitHub Actions CI for Python 3.9, 3.10, 3.11, 3.12
