"""Offline wire-request, response, and streaming conformance corpus."""

from __future__ import annotations

import asyncio
import csv
import inspect
import json
import typing
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List

import pytest

from exa_py.api import AsyncExa, Exa

from .conftest import path_matches_template, read_json_lines, write_or_compare

ROOT = Path(__file__).parent
INVENTORY = ROOT / "exa-py-surface.tsv"
GOLDEN = ROOT / "goldens" / "requests.json"
RESPONSE_GOLDEN = ROOT / "goldens" / "responses.json"
RESPONSE_FIXTURES = ROOT / "fixtures" / "responses.json"


def _inventory() -> list[dict[str, str]]:
    with INVENTORY.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _endpoint_rows() -> list[dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    for row in _inventory():
        endpoint = row["http_endpoint"]
        if endpoint == "n/a":
            continue
        previous = rows.get(endpoint)
        preferred = {
            "search",
            "find_similar",
            "get_contents",
            "answer",
            "create",
            "get",
            "list",
            "update",
            "delete",
            "cancel",
            "content",
        }
        if previous is None or (
            row["namespace"].startswith("Exa")
            and previous["namespace"].startswith("AsyncExa")
        ) or (
            row["namespace"].startswith("Exa")
            and row["method"] in preferred
            and previous["method"] not in preferred
        ):
            rows[endpoint] = row
    return list(rows.values())


def _resolve(client: Any, namespace: str, method: str, endpoint: str) -> Any:
    if endpoint.endswith("/entities"):
        return getattr(client.beta.agent.monitors.entities, method)
    if endpoint.endswith("/changes"):
        return getattr(client.beta.agent.monitors.changes, method)
    if "/snapshot" in endpoint:
        return getattr(client.beta.agent.monitors.snapshots, method)
    if endpoint.endswith("/attempts"):
        return getattr(client.websets.webhooks.attempts, method)
    if ".agent.monitors" in namespace:
        return getattr(client.beta.agent.monitors, method)
    path = namespace.split(".")
    if path[0] in {"Exa", "AsyncExa"}:
        path = path[1:]
    current = client
    for part in path:
        current = getattr(current, part)
    return getattr(current, method)


def _value(name: str, annotation: Any = inspect.Parameter.empty) -> Any:
    """Build a deterministic value for every public parameter type."""
    if name == "contents":
        return {
            "text": {"max_characters": 1},
            "summary": {"schema": {"type": "object", "properties": {}}},
        }
    if name == "summary":
        return {"schema": {"type": "object", "properties": {}}}
    if name == "extras":
        return {"links": True}
    if name == "subpages":
        return {"include": ["https://example.com"]}
    if name in {"params", "options", "config"}:
        return {"query": "conformance-value"}
    if name in {"output_schema", "outputSchema"}:
        return {"type": "object", "properties": {}}
    if name in {"input", "body", "metadata", "budget"}:
        return {"value": "conformance-value"}
    if name == "data_sources":
        return []
    if name == "entities":
        return []
    if name == "fields":
        return []
    if name in {"query", "url", "instructions", "system_prompt", "run_id"}:
        return "conformance-value"
    if name in {
        "include_domains",
        "exclude_domains",
        "include_text",
        "exclude_text",
        "additional_queries",
        "flags",
        "types",
        "expand",
    }:
        return ["conformance-value", "conformance-value-2"]
    if name in {"effort", "model", "category", "type", "status", "event_type"}:
        return "minimal" if name == "effort" else "conformance-value"
    if name in {"moderation", "exclude_source_domain", "successful"}:
        return True
    if name.endswith("_id") or name in {"id", "snapshot_id", "research_id"}:
        return "conformance-id"
    if name in {"start_date", "end_date"}:
        return "2025-01-01T00:00:00Z"
    if name == "betas":
        return ["agent-monitors-2026-08-04"]
    origin = typing.get_origin(annotation)
    args = typing.get_args(annotation)
    if origin is typing.Literal:
        return args[0]
    if origin in {list, tuple, typing.List, typing.Sequence}:
        return [_value(name, args[0] if args else Any)] * 2
    if origin is dict or annotation is dict:
        return {"value": "conformance-value"}
    if origin in {typing.Union, typing.Optional}:
        non_none = [arg for arg in args if arg is not type(None)]
        return _value(name, non_none[0] if non_none else Any)
    if annotation is bool:
        return False
    if annotation is int:
        return 1
    if annotation is float:
        return 1.0
    if name in {"limit", "num_results", "timeout", "poll_interval"}:
        return 1
    if name in {"stream", "events"}:
        return False
    if name == "text":
        return True
    return "conformance-value"


def _evaluated_signature(method: Any) -> inspect.Signature:
    """Resolve annotations on Python versions without eval_str support."""
    try:
        return inspect.signature(method, eval_str=True)
    except TypeError:
        signature = inspect.signature(method)
        try:
            hints = typing.get_type_hints(method)
        except (NameError, TypeError):
            hints = {}
        parameters = [
            parameter.replace(annotation=hints.get(parameter.name, parameter.annotation))
            for parameter in signature.parameters.values()
        ]
        return signature.replace(
            parameters=parameters,
            return_annotation=hints.get("return", signature.return_annotation),
        )


def _invoke(client: Any, row: dict[str, str]) -> Any:
    method = _resolve(client, row["namespace"], row["method"], row["http_endpoint"])
    signature = _evaluated_signature(method)
    positional: List[Any] = []
    keyword: Dict[str, Any] = {}
    for parameter in signature.parameters.values():
        if (
            parameter.name == "self"
            or parameter.kind
            in {inspect.Parameter.VAR_KEYWORD, inspect.Parameter.VAR_POSITIONAL}
        ):
            continue
        value = _value(parameter.name, parameter.annotation)
        if parameter.name == "urls":
            value = ["https://example.com", "https://example.org"]
        if parameter.name == "csv_data":
            value = None
        if parameter.kind is inspect.Parameter.POSITIONAL_ONLY:
            positional.append(value)
        else:
            keyword[parameter.name] = value
    result = method(*positional, **keyword)
    if inspect.isgenerator(result):
        next(result, None)
    return result


async def _invoke_async(client: Any, row: dict[str, str]) -> Any:
    """Invoke an async endpoint with the same generated arguments."""
    method = _resolve(client, row["namespace"], row["method"], row["http_endpoint"])
    signature = _evaluated_signature(method)
    positional: List[Any] = []
    keyword: Dict[str, Any] = {}
    for parameter in signature.parameters.values():
        if parameter.name == "self" or parameter.kind in {
            inspect.Parameter.VAR_KEYWORD,
            inspect.Parameter.VAR_POSITIONAL,
        }:
            continue
        value = _value(parameter.name, parameter.annotation)
        if parameter.name == "urls":
            value = ["https://example.com", "https://example.org"]
        if parameter.name == "csv_data":
            value = None
        if parameter.kind is inspect.Parameter.POSITIONAL_ONLY:
            positional.append(value)
        else:
            keyword[parameter.name] = value
    result = await method(*positional, **keyword)
    if inspect.isasyncgen(result):
        await result.aclose()
    return result


def _public_shape(value: Any) -> Any:
    """Serialize the public parsed shape without unstable object details."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return {"type": type(value).__name__, "value": value}
    if isinstance(value, Enum):
        return {"type": type(value).__name__, "value": value.value}
    if isinstance(value, (date, datetime)):
        return {"type": type(value).__name__, "value": value.isoformat()}
    if isinstance(value, (list, tuple)):
        return {
            "type": type(value).__name__,
            "items": [_public_shape(item) for item in value],
        }
    if isinstance(value, dict):
        return {
            "type": type(value).__name__,
            "attributes": {
                str(key): _public_shape(item)
                for key, item in sorted(value.items(), key=lambda item: str(item[0]))
            },
        }
    if hasattr(value, "value") and not hasattr(value, "__dict__"):
        return {"type": type(value).__name__, "value": value.value}
    attributes = {
        name: _public_shape(item)
        for name, item in sorted(vars(value).items())
        if not name.startswith("_")
    }
    return {"type": type(value).__name__, "attributes": attributes}


def _set_outcome(transport: Any, outcome: str) -> None:
    """Attach the public call outcome to the request captured at the seam."""
    if transport.requests:
        transport.requests[-1].outcome = outcome


@pytest.mark.parametrize("row", _endpoint_rows(), ids=lambda row: row["http_endpoint"])
def test_every_inventory_endpoint_is_driven(
    row: dict[str, str], offline_transport: Any
) -> None:
    """Drive each endpoint through its public client method."""
    client = Exa(api_key="dummy-api-key")
    try:
        if row["http_endpoint"] == "POST /findSimilar":
            with pytest.warns(DeprecationWarning, match="find_similar"):
                _invoke(client, row)
        else:
            _invoke(client, row)
    except Exception as error:
        _set_outcome(offline_transport, f"raised:{type(error).__name__}")
    captured = offline_transport.requests[-1]
    method, template = row["http_endpoint"].split(" ", 1)
    assert captured.method == method
    assert path_matches_template(captured.url, template)


def test_every_inventory_endpoint_has_response_fixture() -> None:
    fixtures = {
        item["endpoint"]: item["payload"] for item in read_json_lines(RESPONSE_FIXTURES)
    }
    driven = {row["http_endpoint"] for row in _endpoint_rows()}
    assert driven <= set(fixtures)


@pytest.mark.asyncio
async def test_async_search_and_answer_streams(offline_transport: Any) -> None:
    """Record the async streaming boundary for search and answer."""
    offline_transport.streaming = True
    client = AsyncExa(api_key="dummy-api-key")
    for method, args in (
        ("stream_search", ("conformance query",)),
        ("stream_answer", ("conformance question",)),
    ):
        stream = await getattr(client, method)(*args)
        async for _ in stream:
            pass
    assert [request.mode for request in offline_transport.requests] == [
        "async",
        "async",
    ]


def test_streaming_search_and_answer(offline_transport: Any) -> None:
    """Record the sync streaming boundary for search and answer."""
    offline_transport.streaming = True
    client = Exa(api_key="dummy-api-key")
    for method, args in (
        ("stream_search", ("conformance query",)),
        ("stream_answer", ("conformance question",)),
    ):
        stream = getattr(client, method)(*args)
        for _ in stream:
            pass
    assert [request.mode for request in offline_transport.requests] == [
        "sync",
        "sync",
    ]


def test_search_and_answer_stream_flags_raise() -> None:
    """Pin the current explicit error for stream=True convenience methods."""
    client = Exa(api_key="dummy-api-key")
    with pytest.raises(ValueError):
        client.search("query", stream=True)
    with pytest.raises(ValueError):
        client.answer("question", stream=True)


def test_find_similar_deprecation_warning(offline_transport: Any) -> None:
    """Pin the public deprecation warning emitted by find_similar."""
    offline_transport.payload = {"results": []}
    with pytest.warns(DeprecationWarning, match="find_similar"):
        Exa(api_key="dummy-api-key").find_similar("https://example.com")


def test_response_models_parse_synthetic_payload(offline_transport: Any) -> None:
    """Pin public response attributes and cost conversion at the wire seam."""
    offline_transport.payload = {
        "requestId": "request-1",
        "results": [{"id": "result-1", "url": "https://example.com", "title": "Example"}],
        "costDollars": {"total": 0.125},
    }
    response = Exa(api_key="dummy-api-key").search("query")
    assert response.results[0].id == "result-1"
    assert response.results[0].title == "Example"
    assert response.cost_dollars.total == 0.125


def test_request_golden(offline_transport: Any) -> None:
    """Record or compare the complete serialized request corpus."""
    client = Exa(api_key="dummy-api-key")
    responses: list[dict[str, Any]] = []
    for row in _endpoint_rows():
        before = len(offline_transport.requests)
        try:
            if row["http_endpoint"] == "POST /findSimilar":
                with pytest.warns(DeprecationWarning, match="find_similar"):
                    result = _invoke(client, row)
            else:
                result = _invoke(client, row)
            outcome = "ok"
            parsed = _public_shape(result)
        except Exception as error:
            outcome = f"raised:{type(error).__name__}"
            parsed = None
            _set_outcome(offline_transport, outcome)
        assert len(offline_transport.requests) == before + 1
        captured = offline_transport.requests[-1]
        responses.append(
            {
                "mode": captured.mode,
                "method": captured.method,
                "path": captured.url.split("?", 1)[0].split("api.exa.ai", 1)[-1],
                "outcome": outcome,
                "response": parsed,
            }
        )
    asyncio.run(_async_request_corpus())
    write_or_compare(GOLDEN, [request.as_dict() for request in offline_transport.requests])
    write_or_compare(RESPONSE_GOLDEN, responses)


def test_sync_async_request_parity() -> None:
    """Require sync and async endpoint wire requests to remain equivalent."""
    expected = read_json_lines(GOLDEN)
    async_requests, async_responses = asyncio.run(_async_request_corpus())
    assert len(expected) == len(async_requests) == len(_endpoint_rows())
    for left, right in zip(expected, async_requests):
        assert left["method"] == right["method"]
        assert left["url"].split("?", 1)[0] == right["url"].split("?", 1)[0]
        assert (
            None
            if left["body"] is None
            else json.loads(left["body"])
        ) == (
            None
            if right["body"] is None
            else json.loads(right["body"])
        )
    expected_responses = read_json_lines(RESPONSE_GOLDEN)
    assert [item["response"] for item in expected_responses] == [
        item["response"] for item in async_responses
    ]


async def _async_request_corpus() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Drive every inventory endpoint through AsyncExa."""
    import httpx

    from .conftest import OfflineTransport

    capture = OfflineTransport()
    capture.response_fixtures = {
        item["endpoint"]: item["payload"] for item in read_json_lines(RESPONSE_FIXTURES)
    }
    client = AsyncExa(api_key="dummy-api-key")
    responses: list[dict[str, Any]] = []
    original = httpx.AsyncHTTPTransport.handle_async_request
    httpx.AsyncHTTPTransport.handle_async_request = capture.handle_async_request
    try:
        for row in _endpoint_rows():
            before = len(capture.requests)
            try:
                if row["http_endpoint"] == "POST /findSimilar":
                    with pytest.warns(DeprecationWarning, match="find_similar"):
                        result = await _invoke_async(client, row)
                else:
                    result = await _invoke_async(client, row)
                outcome = "ok"
                parsed = _public_shape(result)
            except Exception as error:
                outcome = f"raised:{type(error).__name__}"
                parsed = None
                _set_outcome(capture, outcome)
            assert len(capture.requests) == before + 1
            captured = capture.requests[-1]
            responses.append(
                {
                    "mode": captured.mode,
                    "method": captured.method,
                    "path": captured.url.split("?", 1)[0].split("api.exa.ai", 1)[-1],
                    "outcome": outcome,
                    "response": parsed,
                }
            )
    finally:
        httpx.AsyncHTTPTransport.handle_async_request = original
    return [request.as_dict() for request in capture.requests], responses
