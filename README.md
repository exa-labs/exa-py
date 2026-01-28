# Exa Python SDK

[![PyPI version](https://img.shields.io/pypi/v/exa-py.svg)](https://pypi.org/project/exa-py/)
[![Downloads](https://img.shields.io/pypi/dm/exa-py.svg)](https://pypi.org/project/exa-py/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

The official Python SDK for [Exa](https://exa.ai), the web search API for AI.

**[Documentation](https://docs.exa.ai)** | **[Dashboard](https://dashboard.exa.ai)**

## Install

```bash
pip install exa-py
```

Requires Python 3.9+

## Quick Start

```python
from exa_py import Exa

exa = Exa(api_key="your-api-key")

# Search the web
results = exa.search("best restaurants in SF")

# Search and get page contents
results = exa.search_and_contents("latest AI research papers")

# Find similar pages
results = exa.find_similar("https://example.com")

# Get contents from URLs
results = exa.get_contents(["https://example.com"])

# Ask a question
response = exa.answer("What is the capital of France?")
```

## Search

```python
# Basic search
results = exa.search("machine learning startups")

# With filters
results = exa.search(
    "climate tech news",
    num_results=20,
    start_published_date="2024-01-01",
    include_domains=["techcrunch.com", "wired.com"]
)

# Search and get contents in one call
results = exa.search_and_contents(
    "best python libraries",
    text=True,
    highlights=True
)
```

## Contents

```python
# Get text from URLs
results = exa.get_contents(
    ["https://example.com"],
    text=True
)

# Get summaries
results = exa.get_contents(
    ["https://example.com"],
    summary=True
)

# Get highlights (key passages)
results = exa.get_contents(
    ["https://example.com"],
    highlights={"num_sentences": 3}
)
```

## Find Similar

```python
# Find pages similar to a URL
results = exa.find_similar("https://example.com")

# Exclude the source domain
results = exa.find_similar(
    "https://example.com",
    exclude_source_domain=True
)

# With contents
results = exa.find_similar_and_contents(
    "https://example.com",
    text=True
)
```

## Answer

```python
# Get an answer with citations
response = exa.answer("What caused the 2008 financial crisis?")
print(response.answer)

# Stream the response
for chunk in exa.stream_answer("Explain quantum computing"):
    print(chunk, end="", flush=True)
```

## Async

```python
from exa_py import AsyncExa

exa = AsyncExa(api_key="your-api-key")

results = await exa.search("async search example")
```

## Research

For complex research tasks with structured output:

```python
response = exa.research.create_task(
    instructions="Summarize recent advances in fusion energy",
    output_schema={
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "key_developments": {"type": "array", "items": {"type": "string"}}
        }
    }
)
```

## More

See the [full documentation](https://docs.exa.ai) for all features including websets, filters, and advanced options.
