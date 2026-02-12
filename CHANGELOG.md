# Changelog

All notable changes to the exa-py SDK will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Custom exception hierarchy for better error handling:
  - `ExaError` - Base exception for all SDK errors
  - `ExaAPIError` - API returned an error response
  - `ExaAuthenticationError` - Invalid or missing API key (401/403)
  - `ExaRateLimitError` - Rate limit exceeded (429) with `retry_after` attribute
  - `ExaNotFoundError` - Resource not found (404)
  - `ExaServerError` - Server errors (5xx)
  - `ExaValidationError` - Invalid parameters
  - `ExaTimeoutError` - Request timeout with `timeout` attribute
  - `ExaNetworkError` - Connection issues
- Automatic retry with exponential backoff for transient failures
- Configurable timeout for all requests (default: 60 seconds)
- Configuration options: `timeout`, `max_retries`, `retry_on_status`, `backoff_factor`
- Async context manager support: `async with AsyncExa() as exa:`
- `close()` method for AsyncExa to properly cleanup resources
- Quick Start Guide (`QUICKSTART.md`)
- This changelog

### Changed
- **BREAKING**: `AsyncExa` parameter renamed from `api_base` to `base_url` for consistency with `Exa`
- Sync client now has a default timeout of 60 seconds (was infinite)
- Async client timeout is now configurable (was hardcoded to 600 seconds)
- Error responses now raise specific exception types instead of generic `ValueError`
- Improved error messages with request IDs for debugging

### Fixed
- Missing `httpx` dependency in `setup.py` (was only in `pyproject.toml`)
- Sync requests could hang indefinitely (now have default 60s timeout)
- Inconsistent parameter naming between sync and async clients

## [2.0.2] - 2024-12-XX

### Added
- Highlights support in search results
- Research API with streaming events
- Websets API for data management

### Fixed
- Various bug fixes and improvements

## [2.0.1] - 2024-XX-XX

### Fixed
- Minor bug fixes

## [2.0.0] - 2024-XX-XX

### Added
- Initial release of exa-py v2
- Search API with neural, keyword, and hybrid search
- Answer API with citations
- Find Similar API
- Get Contents API
- Streaming support for answers
- Full async support with AsyncExa
- Pydantic models for type safety
- Research API (beta)
- Websets API (beta)

---

## Migration Guide

### From v1.x to v2.x

```python
# Old (v1.x)
from metaphor_python import Metaphor
client = Metaphor(api_key="...")

# New (v2.x)
from exa_py import Exa
client = Exa(api_key="...")
```

### Error Handling Migration

```python
# Old - catching generic ValueError
try:
    results = exa.search("query")
except ValueError as e:
    print(f"Error: {e}")

# New - catching specific exceptions
from exa_py.exceptions import ExaRateLimitError, ExaAuthenticationError

try:
    results = exa.search("query")
except ExaAuthenticationError:
    print("Check your API key")
except ExaRateLimitError as e:
    time.sleep(e.retry_after or 60)
    # Retry...
```

### AsyncExa Parameter Change

```python
# Old
async_exa = AsyncExa(api_key="...", api_base="https://api.exa.ai")

# New
async_exa = AsyncExa(api_key="...", base_url="https://api.exa.ai")
```
