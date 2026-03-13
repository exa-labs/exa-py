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
    contents={"highlights": True}
)

# Ask a question
response = exa.answer("What is the capital of France?")
```

## Search

```python
results = exa.search(
    "machine learning startups",
    contents={"highlights": True}
)
```

```python
results = exa.search(
    "climate tech news",
    num_results=20,
    start_published_date="2024-01-01",
    include_domains=["techcrunch.com", "wired.com"],
    contents={"highlights": True}
)
```

```python
results = exa.search(
    "What are the latest battery breakthroughs?",
    type="deep",
    system_prompt="Prefer official sources and avoid duplicate results",
    output_schema={
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "key_companies": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["summary", "key_companies"],
    },
)
print(results.output.content if results.output else None)
```

Deep `output_schema` modes:
- `{"type": "text", "description": "..."}`: return plain text in `output.content`
- `{"type": "object", ...}`: return structured JSON in `output.content`

Deep search also supports `system_prompt` to guide both the search process and the final returned result, for example by preferring certain sources, emphasizing novel findings, avoiding duplicates, or constraining output style.

For `type: "object"`, deep search currently enforces:
- max nesting depth: `2`
- max total properties: `10`

Deep search variants:
- `deep`: light mode
- `deep-reasoning`: base reasoning mode

## Contents

```python
results = exa.get_contents(
    ["https://docs.exa.ai"],
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
    highlights=True
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

## More

See the [full documentation](https://docs.exa.ai) for all features including websets, filters, and advanced options.
