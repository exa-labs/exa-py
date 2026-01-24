# Quick Start Guide

Get up and running with the Exa Python SDK in 5 minutes.

## Installation

```bash
pip install exa_py
```

## Get Your API Key

1. Sign up at [exa.ai](https://exa.ai)
2. Go to your [dashboard](https://dashboard.exa.ai) to get your API key

## Set Up Your API Key

Set your API key as an environment variable:

```bash
export EXA_API_KEY="your-api-key-here"
```

Or pass it directly when creating the client:

```python
from exa_py import Exa

exa = Exa(api_key="your-api-key-here")
```

## Your First Search

```python
from exa_py import Exa

# Initialize the client (uses EXA_API_KEY env var)
exa = Exa()

# Search for something
results = exa.search("latest developments in AI")

# Print the results
for result in results.results:
    print(f"Title: {result.title}")
    print(f"URL: {result.url}")
    print(f"Text: {result.text[:200]}...")  # First 200 chars
    print("---")
```

## Common Use Cases

### Search with Filters

```python
results = exa.search(
    "machine learning tutorials",
    num_results=5,
    include_domains=["arxiv.org", "github.com"],
    start_published_date="2024-01-01",
)
```

### Get Answers with Citations

```python
response = exa.answer("What is retrieval-augmented generation (RAG)?")

print(f"Answer: {response.answer}")
print("\nSources:")
for citation in response.citations:
    print(f"  - {citation.title}: {citation.url}")
```

### Find Similar Content

```python
results = exa.find_similar(
    "https://arxiv.org/abs/2005.11401",  # GPT-3 paper
    num_results=10,
)

for result in results.results:
    print(f"{result.title}: {result.url}")
```

### Async Usage

```python
import asyncio
from exa_py import AsyncExa

async def main():
    async with AsyncExa() as exa:
        results = await exa.search("AI news today")
        for result in results.results:
            print(result.title)

asyncio.run(main())
```

## Error Handling

```python
from exa_py import Exa
from exa_py.exceptions import (
    ExaAuthenticationError,
    ExaRateLimitError,
    ExaAPIError,
)

exa = Exa()

try:
    results = exa.search("query")
except ExaAuthenticationError:
    print("Invalid API key - check your EXA_API_KEY")
except ExaRateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after} seconds")
except ExaAPIError as e:
    print(f"API error {e.status_code}: {e.message}")
```

## Configuration Options

```python
exa = Exa(
    api_key="your-key",          # API key (or use EXA_API_KEY env var)
    timeout=30,                   # Request timeout in seconds (default: 60)
    max_retries=5,               # Retry attempts (default: 3)
    backoff_factor=1.0,          # Exponential backoff multiplier (default: 0.5)
)
```

## Next Steps

- [Full API Reference](https://docs.exa.ai/reference)
- [Examples](./examples/)
- [Research API Guide](./examples/research/)
- [Websets API Guide](./examples/websets/)

## Need Help?

- [Documentation](https://docs.exa.ai)
- [GitHub Issues](https://github.com/exa-labs/exa-py/issues)
- [Discord Community](https://discord.gg/exa)
