# Include URLs and Exclude URLs Implementation

## Summary

Added support for `include_urls` and `exclude_urls` parameters to all search-related methods in the Exa Python SDK, following the same pattern as the existing `include_domains` and `exclude_domains` parameters.

## Changes Made

### 1. Core API Changes (`exa_py/api.py`)

#### Option Type Definitions
- Added `include_urls` and `exclude_urls` to `SEARCH_OPTIONS_TYPES` dictionary
- Added `include_urls` and `exclude_urls` to `FIND_SIMILAR_OPTIONS_TYPES` dictionary

#### Function Signatures Updated
The following methods now include `include_urls` and `exclude_urls` parameters:

##### Main Exa Class
- `search()` - Basic search functionality
- `find_similar()` - Find similar pages to a given URL
- All `search_and_contents()` overloads (8 different overloads)
- All `find_similar_and_contents()` overloads (8 different overloads)

##### AsyncExa Class
- `search()` - Async version of basic search
- `find_similar()` - Async version of find similar

##### OpenAI Integration
- `create_with_rag()` function in the OpenAI wrapper
- Updated `exa_kwargs` dictionary construction
- Updated `search_and_contents()` call within `_create_with_tool()`

#### Documentation Updates
- Updated docstrings for all modified functions
- Added parameter descriptions following the existing pattern:
  - `include_urls (List[str], optional): URLs to include in the search.`
  - `exclude_urls (List[str], optional): URLs to exclude from the search.`

### 2. Example Updates

#### `examples/basic_search.py`
- Added example using `include_urls` with specific URL patterns
- Added example using `exclude_urls` to avoid spam sites
- Combined usage with existing `include_domains` parameter

#### `examples/async/basic_search.py`
- Added async examples for both `include_urls` and `exclude_urls`
- Demonstrates proper async/await usage with new parameters

### 3. Documentation Updates

#### `README.md`
- Added examples in the "Common requests" section:
  ```python
  # search with URL filters
  results = exa.search("This is a Exa query:", include_urls=["https://arxiv.org/*", "https://openai.com/blog/*"])
  
  # search excluding specific URLs
  results = exa.search("This is a Exa query:", exclude_urls=["https://example-spam-site.com/*"])
  ```

## Usage Examples

### Basic Search with URL Filtering
```python
# Include specific URL patterns
results = exa.search(
    "machine learning research",
    include_urls=["https://arxiv.org/*", "https://openai.com/blog/*"]
)

# Exclude specific URL patterns
results = exa.search(
    "technology news",
    exclude_urls=["https://spam-site.com/*"],
    include_domains=["techcrunch.com", "arstechnica.com"]
)
```

### Find Similar with URL Filtering
```python
results = exa.find_similar(
    "https://example.com/article",
    include_urls=["https://trusted-site.com/*"],
    exclude_urls=["https://untrusted-site.com/*"]
)
```

### Search and Contents with URL Filtering
```python
results = exa.search_and_contents(
    "AI research papers",
    include_urls=["https://arxiv.org/*"],
    text=True
)
```

## Parameter Behavior

- `include_urls` and `exclude_urls` follow the same exclusivity pattern as domain filters
- URL patterns support wildcards (e.g., `https://example.com/*`)
- These parameters can be combined with existing domain filters
- All parameters are optional and typed as `Optional[List[str]]`

## Backward Compatibility

- All changes are backward compatible
- Existing code continues to work without modification
- New parameters are optional and default to `None`

## Implementation Notes

- The implementation maintains consistency with existing `include_domains`/`exclude_domains` patterns
- All function overloads have been updated to maintain proper type checking
- Documentation follows the established format and style
- Examples demonstrate real-world usage scenarios