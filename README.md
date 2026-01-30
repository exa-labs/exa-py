# Exa Python SDK

[![PyPI version](https://img.shields.io/pypi/v/exa-py.svg)](https://pypi.org/project/exa-py/)

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
results = exa.search(
    "blog post about artificial intelligence",
    type="auto",
    contents={"text": True}
)

# Find similar pages
results = exa.find_similar(
    "https://paulgraham.com/greatwork.html",
    contents={"text": True}
)

# Ask a question
response = exa.answer("What is the capital of France?")
```

## Search

```python
results = exa.search(
    "machine learning startups",
    contents={"text": True}
)
```

```python
results = exa.search(
    "climate tech news",
    num_results=20,
    start_published_date="2024-01-01",
    include_domains=["techcrunch.com", "wired.com"],
    contents={"text": True}
)
```

## Contents

```python
results = exa.get_contents(
    ["https://openai.com/research"],
    text=True
)
```

```python
results = exa.get_contents(
    ["https://stripe.com/docs/api"],
    summary=True
)
```

```python
results = exa.get_contents(
    ["https://arxiv.org/abs/2303.08774"],
    highlights={"max_characters": 500}
)
```

## Find Similar

```python
results = exa.find_similar(
    "https://paulgraham.com/greatwork.html",
    contents={"text": True}
)
```

```python
results = exa.find_similar(
    "https://amistrongeryet.substack.com/p/are-we-on-the-brink-of-agi",
    exclude_source_domain=True,
    contents={"text": True}
)
```

## Answer

```python
response = exa.answer("What caused the 2008 financial crisis?")
print(response.answer)
```

```python
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
response = exa.research.create(
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
