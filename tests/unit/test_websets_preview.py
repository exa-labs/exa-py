"""Preview request compatibility and typed sample items on both transports."""

import inspect
import json

import httpx
import pytest
import pytest_asyncio
import requests
from pydantic import ValidationError

from exa_py import AsyncExa, Exa
from exa_py.websets import types


@pytest_asyncio.fixture(params=["sync", "async"])
async def sdk(request, monkeypatch):
    captured = []
    reply = {}

    def record(method, url, body, headers):
        captured.append({
            "method": method,
            "url": str(url),
            "body": json.loads(body) if body else None,
            "headers": {key.lower(): value for key, value in headers.items()},
        })

    if request.param == "sync":
        def send(session, prepared, **kwargs):
            record(prepared.method, prepared.url, prepared.body, prepared.headers)
            response = requests.Response()
            response.status_code = 200
            response._content = json.dumps(reply).encode()
            return response

        monkeypatch.setattr(requests.Session, "send", send)
        yield Exa("test-key", base_url="https://api.example.com"), captured, reply
    else:
        async def send(client, prepared, **kwargs):
            record(prepared.method, prepared.url, prepared.content, prepared.headers)
            return httpx.Response(200, json=reply, request=prepared)

        monkeypatch.setattr(httpx.AsyncClient, "send", send)
        async with AsyncExa("test-key", api_base="https://api.example.com") as exa:
            yield exa, captured, reply


async def invoke(method, *args, **kwargs):
    """Exercise the same public operation through either client."""
    result = method(*args, **kwargs)
    return await result if inspect.isawaitable(result) else result


@pytest.mark.asyncio
@pytest.mark.parametrize("typed", [False, True])
@pytest.mark.parametrize("search_items", [None, False, True])
async def test_preview_search_wrapper_and_items(sdk, typed, search_items):
    exa, captured, reply = sdk
    reply.update({
        "search": {"entity": {"type": "company"}, "criteria": [{"description": "Climate"}]},
        "enrichments": [{"description": "Website", "format": "url"}],
        "items": [{
            "id": "preview_1", "properties": {
                "type": "company", "url": "https://example.com", "description": "Climate company",
                "company": {"name": "Example"},
            },
            "createdAt": "2026-01-01T00:00:00Z",
        }],
    })
    body = {"search": {"query": "Climate companies", "entity": {"type": "company"}, "count": 1}}
    params = types.PreviewWebsetParameters(**body) if typed else body
    kwargs = {} if search_items is None else {"search": search_items}
    result = await invoke(exa.websets.preview, params, **kwargs)
    assert captured[-1]["body"] == body
    assert captured[-1]["method"] == "POST"
    suffix = "" if search_items is None else f"?search={str(search_items).lower()}"
    assert captured[-1]["url"] == "https://api.example.com/websets/v0/websets/preview" + suffix
    assert result.search.entity.type == "company"
    assert result.enrichments[0].format == "url"
    assert result.items[0].properties.company.name == "Example"
    assert result.items[0].created_at.year == 2026


@pytest.mark.asyncio
async def test_legacy_preview_remains_supported(sdk):
    exa, captured, reply = sdk
    reply.update({"search": {"entity": {"type": "company"}, "criteria": []}, "enrichments": []})
    params = types.PreviewWebsetParameters(query="Climate companies", entity={"type": "company"})
    result = await invoke(exa.websets.preview, params)
    assert captured[-1]["body"] == {"query": "Climate companies", "entity": {"type": "company"}}
    assert result.items == []


def test_preview_validates_search_input():
    with pytest.raises(ValidationError, match="query"):
        types.PreviewWebsetParameters(search={"count": 1})
    with pytest.raises(ValidationError, match="query"):
        types.PreviewWebsetParameters()


@pytest.mark.asyncio
@pytest.mark.parametrize("search", [False, True])
@pytest.mark.parametrize("override", [None, False])
async def test_preview_query_options_skip_none_and_preserve_false(sdk, search, override):
    exa, captured, reply = sdk
    reply.update({"search": {"entity": {"type": "company"}, "criteria": []}, "enrichments": []})
    await invoke(exa.websets.preview, {"search": {"query": "Climate companies"}},
                 search=search, extra_query={"search": override})
    expected = search if override is None else override
    assert captured[-1]["url"].endswith("?search=" + str(expected).lower())


@pytest.mark.parametrize("query", ["", "q" * 5001], ids=["empty", "too_long"])
def test_nested_preview_query_length_is_validated(query):
    with pytest.raises(ValidationError, match="query"):
        types.PreviewWebsetParameters(search={"query": query})


@pytest.mark.parametrize("length", [1, 5000])
def test_nested_preview_query_boundary_is_supported(length):
    params = types.PreviewWebsetParameters(search={"query": "q" * length})
    assert params.search.query == "q" * length


@pytest.mark.parametrize("count", [0, 11])
def test_nested_preview_count_is_validated(count):
    with pytest.raises(ValidationError, match="count"):
        types.PreviewWebsetParameters(search={"query": "Climate companies", "count": count})


@pytest.mark.asyncio
async def test_preview_preserves_unknown_item_properties(sdk):
    exa, captured, reply = sdk
    reply.update({
        "search": {"entity": {"type": "company"}, "criteria": []}, "enrichments": [],
        "items": [{
            "id": "preview_1",
            "properties": {
                "type": "future", "url": "https://example.com",
                "description": "Future entity", "futureField": "value",
            },
            "createdAt": "2026-01-01T00:00:00Z",
        }],
    })
    types.WebsetItemPreview.model_rebuild(force=True)
    result = await invoke(exa.websets.preview, {"search": {"query": "Climate companies"}})
    properties = result.items[0].properties
    assert isinstance(properties, types.UnknownWebsetItemProperties)
    assert properties.type == "future"
    assert properties.model_dump()["futureField"] == "value"
