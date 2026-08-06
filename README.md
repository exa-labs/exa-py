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
    type="auto",
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

```python
for chunk in exa.stream_search(
    "What are the latest battery breakthroughs?",
    type="auto",
):
    if chunk.content:
        print(chunk.content, end="", flush=True)
```

Search `output_schema` modes:
- `{"type": "text", "description": "..."}`: return plain text in `output.content`
- `{"type": "object", ...}`: return structured JSON in `output.content`

`system_prompt` and `output_schema` are supported on every search type.
Search streaming is available via `stream_search(...)`, which yields OpenAI-style chat completion chunks.

For `type: "object"`, search currently enforces:
- max nesting depth: `2`
- max total properties: `10`

Deep search variants that also support `additional_queries`:
- `deep-lite`
- `deep`
- `deep-reasoning`

## Contents

```python
results = exa.get_contents(
    ["https://docs.exa.ai"],
    text=True
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

## Agent API

The Agent API is available without a beta header.

```python
run = exa.agent.runs.create(
    query="Find engineering leaders at AI infrastructure companies that raised a Series A or B in the last 6 months.",
    output_schema={
        "type": "object",
        "properties": {
            "people": {
                "type": "array",
                "maxItems": 10,
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "contact_email": {"type": "string", "format": "email"},
                        "linkedin_url": {"type": "string", "format": "uri"},
                    },
                    "required": ["name", "linkedin_url"],
                },
            }
        },
        "required": ["people"],
    },
    effort="auto",
)

run = exa.agent.runs.poll_until_finished(run.id)
print(run.output.structured if run.output else None)
```

For Agent Max, use the beta namespace and pass the beta token explicitly:

```python
from exa_py import Exa
from exa_py.agent import AGENT_MAX_EFFORT_BETA

exa = Exa()
run = exa.beta.agent.runs.create(
    query="Find all companies building browser automation tools in the United States.",
    effort="max",
    budget={"maxCostDollars": 10},
    betas=[AGENT_MAX_EFFORT_BETA],
)
```

## Agent Monitors (Beta)

Agent Monitors use the beta namespace and require the `AGENT_MONITORS_BETA_HEADER` beta identifier (`agent-monitors-2026-08-04`).

An Agent Monitor keeps a table of entities × fields fresh on a cadence: static fields are answered once per entity over the live web, dynamic fields are tracked from news on every refresh.

```python
from exa_py.agent import AGENT_MONITORS_BETA_HEADER

betas = [AGENT_MONITORS_BETA_HEADER]

# Create a monitor. Creation is async: it returns with status "creating"
# and becomes "active" once the first refresh completes.
monitor = exa.beta.agent.monitors.create(
    betas=betas,
    cadence="7d",
    entities=[
        {"name": "Acme Corp", "domain": "acme.com"},
        {"name": "Globex", "domain": "globex.com"},
    ],
    fields=[
        {"name": "ceo", "description": "The company's current CEO"},  # static by default
        {"name": "funding", "description": "New funding rounds", "type": "dynamic"},
    ],
    idempotency_key="my-monitor-1",  # safe retries: same key returns the same monitor
)

# Page the monitor's current entities and their contents.
for view in exa.beta.agent.monitors.entities.list_all(monitor.id, betas=betas):
    print(view.entity.name, view.contents)

# Follow the content change feed (resume later from the page's next_cursor).
changes = exa.beta.agent.monitors.changes.list(
    monitor.id,
    betas=betas,
    since="2026-01-01T00:00:00Z",
)

# One-shot stateless snapshot of a past news window — no monitor created.
snapshot = exa.beta.agent.monitors.snapshots.create_and_wait(
    betas=betas,
    entities=[{"name": "Acme Corp", "domain": "acme.com"}],
    fields=[{"name": "funding", "description": "New funding rounds", "type": "dynamic"}],
    start_date="2026-01-01",
    end_date="2026-01-08",
)
print(snapshot.data)

# Add entities, inspect refresh progress, clean up.
exa.beta.agent.monitors.entities.add(
    monitor.id,
    betas=betas,
    entities=[{"name": "Initech", "domain": "initech.com"}],
)
current = exa.beta.agent.monitors.get(monitor.id, betas=betas)
print(current.status, current.refresh, current.usage)
exa.beta.agent.monitors.delete(monitor.id, betas=betas)
```

## Async

```python
from exa_py import AsyncExa

exa = AsyncExa(api_key="your-api-key")

results = await exa.search("async search example", contents={"highlights": True})
```

## More

See the [full documentation](https://docs.exa.ai) for all features including websets, filters, and advanced options.
