# Exa Python SDK

[![PyPI version](https://img.shields.io/pypi/v/exa-py.svg)](https://pypi.org/project/exa-py/)

The official Python SDK for [Exa](https://exa.ai), the web search API for AI.

**[Documentation](https://exa.ai/docs)** | **[Dashboard](https://dashboard.exa.ai)**

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
    output_schema={"type": "text"},
):
    if chunk.content:
        print(chunk.content, end="", flush=True)
```

Search `output_schema` modes:
- `{"type": "text", "description": "..."}`: return plain text in `output.content`
- `{"type": "object", ...}`: return structured JSON in `output.content`

`system_prompt` and `output_schema` are supported on every search type.
Search streaming is available via `stream_search(...)`, which yields OpenAI-style chat completion chunks.
A search without `output_schema` has no text to stream. Its stream yields one chunk with the results as `citations`.

For `type: "object"`, search currently enforces:
- max nesting depth: `2`
- max total properties: `10`

Deep search variants that also support `additional_queries`:
- `deep-lite`
- `deep`
- `deep-reasoning`

### Raw body fields

Use `extra_body` for per-call search body overrides. Every other method takes it too; see [Request options](#request-options).

```python
result = exa.search("AI research", extra_body={"futureField": True})
```

## Contents

```python
results = exa.get_contents(
    ["https://exa.ai/docs"],
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

## Web Search and Contents tools

Use Exa as a `web_search` tool in an OpenAI or Anthropic loop. Call `web_search()` with no arguments to get Exa's recommended settings for agentic search (`type="auto"` and `contents={"highlights": True}`).

```python
from exa_py import Exa
from openai import OpenAI

exa = Exa()
openai_client = OpenAI()

messages = [{"role": "user", "content": "What's the latest on AI chips?"}]

completion = openai_client.chat.completions.create(
    model="gpt-5.6",
    messages=messages,
    tools=[exa.openai.web_search()],
)

message = completion.choices[0].message
messages.append(message)
messages += exa.openai.handle_tool_calls(message)
```

```python
import anthropic

client = anthropic.Anthropic()
response = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=1024,
    messages=messages,
    tools=[exa.anthropic.web_search()],
)
```

Pass `name` (and optionally `description`) to rename the tool. Anthropic requires tool names to be unique, so a custom name lets the Exa tool run alongside Anthropic's built-in `web_search_20250305` tool:

```python
response = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=1024,
    messages=messages,
    tools=[
        exa.anthropic.web_search(name="exa_web_search"),
        {"type": "web_search_20250305", "name": "web_search", "max_uses": 5},
    ],
)
```

`get_contents` is available in the same namespaces and lets the model read pages it already has URLs for. It takes a list of URLs and accepts every `Exa.get_contents` option:

```python
completion = openai_client.chat.completions.create(
    model="gpt-5.6",
    messages=messages,
    tools=[
        exa.openai.web_search(),
        exa.openai.get_contents(summary=True, livecrawl="preferred"),
    ],
)
```

For the OpenAI Responses API, use `exa.openai.responses.web_search()` and the same `handle_tool_calls` helper. The handlers answer every tool call: calls naming a tool they can't resolve get an `Error: unknown tool "<name>"` output instead of being dropped, so follow-up requests stay valid. If you run other tools alongside Exa's, replace those error outputs with your own results before the next request.

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

For Agent Ultra, set `effort="ultra"`:

```python
from exa_py import Exa

exa = Exa()
run = exa.agent.runs.create(
    query="Find all companies building browser automation tools in the United States.",
    effort="ultra",
    budget={"maxCostDollars": 10},
)
```

## Agent Monitors (Beta)

Agent Monitors use the beta namespace and require the `AGENT_MONITORS_BETA_HEADER` beta identifier (`agent-monitors-2026-08-04`).

An Agent Monitor keeps a table of entities × fields fresh on a cadence.

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
        {"name": "funding", "description": "New funding rounds"},
        {"name": "ceo", "description": "The company's current CEO"},
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

# One-shot backtest of a past news window — no monitor persists.
backtest = exa.beta.agent.monitors.backtests.create_and_wait(
    betas=betas,
    entities=[{"name": "Acme Corp", "domain": "acme.com"}],
    fields=[{"name": "funding", "description": "New funding rounds"}],
    start_time="2026-01-01T00:00:00Z",
    end_time="2026-01-08T00:00:00Z",
)
print(backtest.data)

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

## Request options

Every API method takes three keyword arguments on top of its own, on `Exa` and `AsyncExa` alike:

| Argument        | Effect                                         |
| --------------- | ---------------------------------------------- |
| `extra_body`    | Extra fields merged over the JSON request body |
| `extra_headers` | Extra request headers                          |
| `extra_query`   | Extra query parameters                         |

```python
# Send a field the SDK does not type yet.
exa.get_contents("https://example.com", text=True, extra_body={"futureField": True})

exa.websets.list(
    limit=10,
    extra_query={"futureParam": "value"},
    extra_headers={"X-Request-Source": "nightly"},
)
```

They add to the request the method builds. On a name the method also sets, your value wins.

- `extra_body` is sent with `POST` and `PATCH` requests. Other requests ignore it; use `extra_query` there.
- `extra_query` skips a parameter set to `None` and sends `True` and `False` as `true` and `false`, from both clients.
- A header the SDK sets, such as `User-Agent`, is replaced whatever its case. A header set to `None` is skipped.
- The method you call decides whether the response streams. `stream` is never taken from `extra_body` or `extra_query`, and an extra `Accept` header neither starts a stream nor replaces the `Accept` of a streaming method: call the streaming method instead.
- Helpers that make several requests (`list_all`, `get_all`, `poll_until_finished`, `create_and_wait`, `wait_until_idle`) apply them to each one, so `create_and_wait` sends `extra_body` with the create request and not with its polls. A `cursor` in `extra_query` picks the first page of `list_all` and `get_all`; the helper advances from there.
- A CSV import's upload goes to a presigned URL and receives none of the three.
- The LLM tool helpers (`exa.tools`, `exa.openai`, `exa.anthropic`) pass the options and `timeout` given when you create a tool to every request it makes, for example `exa.openai.web_search(timeout=10, extra_headers={"X-Request-Source": "agent"})`. `run`, `execute` and the `handle_tool_calls` / `handle_tool_use` helpers take none per call.

## Timeouts and cancellation

The sync and async clients default to a 600-second **network inactivity timeout** (not a wall-clock deadline). Set a client-wide value or override it for a search, contents, answer, or streaming call; use `None` at construction to disable it. A per-call `None` inherits the client's value.

```python
from exa_py import Exa

exa = Exa(api_key="your-api-key", timeout=30)
results = exa.search("latest AI developments", timeout=5)
```

A request that exceeds its timeout raises `ExaTimeoutError`, from the sync and the async client alike:

```python
from exa_py import Exa, ExaTimeoutError

exa = Exa(api_key="your-api-key")
try:
    results = exa.search("latest AI developments", timeout=5)
except ExaTimeoutError:
    results = None
```

The error is also an instance of the exception the HTTP library raised, so handlers written for those keep working:

- `AsyncExa`: an `httpx.TimeoutException`.
- `Exa`: a `requests.exceptions.Timeout` while connecting or waiting for the response to start, and a `requests.exceptions.ConnectionError` when the response stalls after it started, as Requests reports it.

With `AsyncExa`, cancel an in-flight operation by cancelling the task awaiting it:

```python
import asyncio
from exa_py import AsyncExa

exa = AsyncExa(api_key="your-api-key")
task = asyncio.create_task(exa.search("latest AI developments"))
task.cancel()
```

When stopping an async search/answer stream early, call `await stream.aclose()` to release its HTTP connection; cancellation while awaiting the next chunk also closes it. The sync client cannot cancel a blocking read from another thread; the timeout bounds each period of network inactivity. Both constructors and per-call overrides require a positive finite timeout when not `None`.

## Warnings

The API can return `warnings` about a request, such as a field it ignores. At the time of writing, search responses carry them, including `stream_search`. A warning never changes the status code or the results. It is for whoever maintains the code that builds the request. Fix the request, and don't pass the warning to a model. The response keeps them in `warnings`.

The client also issues each one as an `ExaWarning` through Python's `warnings` module, attributed to the line of your code that made the call:

```text
app.py:12: ExaWarning: [exa] POST /search IGNORED_FIELD at /startCrawlDate: startCrawlDate is no longer supported and is ignored. Remove it from the request.
```

Python's default filter shows a given warning once per calling line. Silence them, or route them to logging:

```python
import logging
import warnings

from exa_py import ExaWarning

warnings.filterwarnings("ignore", category=ExaWarning)  # silence them
logging.captureWarnings(True)  # or send them to the "py.warnings" logger
```

Each `ExaWarning` has the attributes `warning`, `endpoint`, `method` and `request_id`. `warning` is the `ApiWarning`, with its `code`, `path` and `message`.

Deprecated options raise a `DeprecationWarning` before the request is sent, whether you set them as options or through `extra_body`. At the time of writing, those are `start_crawl_date`, `end_crawl_date`, and the highlights options `num_sentences` and `highlights_per_url`. Python shows a `DeprecationWarning` by default only for code run as `__main__`. Test runners such as pytest show them too.

## More

See the [full documentation](https://exa.ai/docs) for all features including websets, filters, and advanced options.
