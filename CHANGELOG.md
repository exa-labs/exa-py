# Changelog

## [1.14.16] - 2025-01-08

### Added
- Added `include_urls` and `exclude_urls` parameters to search methods
  - Available in `search()`, `search_and_contents()`, `find_similar()`, and `find_similar_and_contents()` methods
  - Both sync and async versions support these new parameters
  - Supports wildcard patterns at the beginning or end of URL patterns (e.g., `*/contact-us/*`, `*.ai`)
  - Use `include_urls` to filter results to only URLs matching specified patterns
  - Use `exclude_urls` to filter out results with URLs matching specified patterns

### Important Constraints
- `include_urls`/`exclude_urls` cannot be used together with `include_domains`/`exclude_domains` in the same request
- `include_urls` and `exclude_urls` cannot be used together in the same request

### Testing
- Added comprehensive test coverage for URL filtering functionality
  - Unit tests for parameter validation in `tests/test_url_filters_unit.py`
  - Integration tests requiring API key in `tests/test_search_api.py`
  - Tests cover both synchronous and asynchronous implementations

### Examples
- Added `examples/url_filtering_example.py` demonstrating various URL filtering patterns
- Added `examples/company_research_url_filtering.py` showing practical company research workflows

### Example Usage
```python
# Include only contact pages
results = exa.search("AI startup", include_urls=["*/contact-us/*", "*/about/*"])

# Exclude blog and news pages
results = exa.search("machine learning", exclude_urls=["*/blog/*", "*/news/*"])

# Filter LinkedIn profiles
results = exa.find_similar(
    "https://www.linkedin.com/in/example/",
    include_urls=["www.linkedin.com/in/*"]
)
```