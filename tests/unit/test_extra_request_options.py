"""extra_headers, extra_query and extra_body reach the request on every client method."""

import asyncio
import inspect
import json
import threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import MagicMock
from urllib.parse import parse_qs, urlsplit

import pytest

import exa_py
from exa_py import AsyncExa, Exa
from exa_py.agent import AgentNamespace
from exa_py.research import ResearchClient
from exa_py.request_options import (
    given_request_options,
    merge_body,
    merge_headers,
    merge_query,
    options_for_next_page,
)

EXTRA = {
    "extra_headers": {"X-Trace": "abc"},
    "extra_query": {"debug": "1"},
    "extra_body": {"futureField": "new"},
}
OPTION_NAMES = ("extra_headers", "extra_query", "extra_body", "extraHeaders", "extraQuery", "extraBody")

_EVENTS = b'id: 1\nevent: agent_run.created\ndata: {"id": "agent_run_1"}\n\n'

_RUN = {
    "id": "agent_run_1",
    "object": "agent_run",
    "status": "completed",
    "createdAt": "2026-05-07T18:31:00.000Z",
    "request": {"query": "test"},
}


class _Api:
    """A local server that records every request and answers with `reply(request)`.

    A reply that is `bytes` is sent as a server-sent event stream, anything
    else as JSON.
    """

    def __init__(self):
        self.requests = []
        self.reply = lambda request: {"results": [], "citations": [], "answer": "ok"}
        api = self

        class Handler(BaseHTTPRequestHandler):
            def _handle(self):
                length = int(self.headers.get("Content-Length", 0))
                text = self.rfile.read(length).decode() if length else ""
                url = urlsplit(self.path)
                request = {
                    "method": self.command,
                    "path": url.path,
                    "query": parse_qs(url.query),
                    "headers": {name.lower(): value for name, value in self.headers.items()},
                    "all_headers": [(name.lower(), value) for name, value in self.headers.items()],
                    "text": text,
                    "body": json.loads(text) if text else None,
                }
                api.requests.append(request)
                reply = api.reply(request)
                if isinstance(reply, bytes):
                    payload, content_type = reply, "text/event-stream"
                else:
                    payload, content_type = json.dumps(reply).encode(), "application/json"
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            do_GET = do_POST = do_PATCH = do_DELETE = _handle

            def log_message(self, *args):
                pass

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._server.daemon_threads = True
        self.url = f"http://127.0.0.1:{self._server.server_address[1]}"
        threading.Thread(target=self._server.serve_forever, daemon=True).start()

    def close(self):
        self._server.shutdown()
        self._server.server_close()


@pytest.fixture
def api():
    server = _Api()
    try:
        yield server
    finally:
        server.close()


def _assert_extras_sent(request, path):
    assert request["path"] == path
    assert request["headers"]["x-trace"] == "abc"
    assert request["query"]["debug"] == ["1"]
    assert request["body"]["futureField"] == "new"
    for name in OPTION_NAMES:
        assert name not in request["body"]


SYNC_CORE_CALLS = [
    ("/search", lambda exa, extra: exa.search("test", **extra)),
    ("/search", lambda exa, extra: exa.stream_search("test", **extra).close()),
    ("/search", lambda exa, extra: exa.search_and_contents("test", **extra)),
    ("/contents", lambda exa, extra: exa.get_contents("https://example.com", **extra)),
    ("/findSimilar", lambda exa, extra: exa.find_similar("https://example.com", **extra)),
    ("/findSimilar", lambda exa, extra: exa.find_similar_and_contents("https://example.com", **extra)),
    ("/answer", lambda exa, extra: exa.answer("test", **extra)),
    ("/answer", lambda exa, extra: exa.stream_answer("test", **extra).close()),
]


@pytest.mark.filterwarnings("ignore::DeprecationWarning")
@pytest.mark.parametrize("path,call", SYNC_CORE_CALLS)
def test_sync_core_methods_send_the_extras(api, path, call):
    call(Exa("test-key", base_url=api.url), EXTRA)
    assert len(api.requests) == 1
    _assert_extras_sent(api.requests[0], path)


async def _close(stream):
    await (await stream).aclose()


ASYNC_CORE_CALLS = [
    ("/search", lambda exa, extra: exa.search("test", **extra)),
    ("/search", lambda exa, extra: _close(exa.stream_search("test", **extra))),
    ("/search", lambda exa, extra: exa.search_and_contents("test", **extra)),
    ("/contents", lambda exa, extra: exa.get_contents("https://example.com", **extra)),
    ("/findSimilar", lambda exa, extra: exa.find_similar("https://example.com", **extra)),
    ("/findSimilar", lambda exa, extra: exa.find_similar_and_contents("https://example.com", **extra)),
    ("/answer", lambda exa, extra: exa.answer("test", **extra)),
    ("/answer", lambda exa, extra: _close(exa.stream_answer("test", **extra))),
]


@pytest.mark.asyncio
@pytest.mark.filterwarnings("ignore::DeprecationWarning")
@pytest.mark.parametrize("path,call", ASYNC_CORE_CALLS)
async def test_async_core_methods_send_the_extras(api, path, call):
    exa = AsyncExa("test-key", api_base=api.url)
    try:
        await call(exa, EXTRA)
    finally:
        await exa.client.aclose()
    assert len(api.requests) == 1
    _assert_extras_sent(api.requests[0], path)


def test_extra_body_replaces_a_field_the_method_sets_and_never_decides_streaming(api):
    exa = Exa("test-key", base_url=api.url)

    exa.answer("test", text=True, extra_body={"text": False, "stream": True})
    exa.stream_answer("test", extra_body={"stream": False, "kept": 1}).close()

    assert api.requests[0]["body"]["text"] is False
    assert api.requests[0]["body"]["stream"] is False
    assert api.requests[1]["body"]["stream"] is True
    assert api.requests[1]["body"]["kept"] == 1


@pytest.mark.parametrize("method", ["GET", "POST", "PATCH", "DELETE"])
def test_sync_request_applies_each_option_where_the_method_can_carry_it(api, method):
    exa = Exa("test-key", base_url=api.url)
    exa.request("/custom", {"a": 1}, method=method, params={"p": "1"}, headers={"X-A": "1"}, **EXTRA)

    request = api.requests[0]
    assert request["method"] == method
    assert request["headers"]["x-a"] == "1"
    assert request["headers"]["x-trace"] == "abc"
    assert request["query"]["debug"] == ["1"]
    if method == "GET":
        assert request["query"]["p"] == ["1"]
    else:
        # Only GET requests send `params`; the others send the extra query alone.
        assert "p" not in request["query"]
    if method in ("POST", "PATCH"):
        assert request["body"] == {"a": 1, "futureField": "new"}
    else:
        assert request["text"] == ""


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["GET", "POST", "PATCH", "DELETE"])
async def test_async_request_applies_each_option_where_the_method_can_carry_it(api, method):
    exa = AsyncExa("test-key", api_base=api.url)
    try:
        await exa.async_request(
            "/custom", {"a": 1}, method=method, params={"p": "1"}, headers={"X-A": "1"}, **EXTRA
        )
    finally:
        await exa.client.aclose()

    request = api.requests[0]
    assert request["method"] == method
    assert request["headers"]["x-a"] == "1"
    assert request["headers"]["x-trace"] == "abc"
    assert request["query"]["debug"] == ["1"]
    if method == "GET":
        assert request["query"]["p"] == ["1"]
    else:
        assert "p" not in request["query"]
    if method in ("POST", "PATCH"):
        assert request["body"] == {"a": 1, "futureField": "new"}
    else:
        assert request["text"] == ""


def test_both_clients_encode_extra_query_values_alike(api):
    api.reply = lambda request: {"data": [], "hasMore": False}
    extra_query = {"flag": True, "off": False, "skipped": None, "limit": None}
    Exa("test-key", base_url=api.url).websets.list(limit=5, extra_query=extra_query)

    async def run_async():
        exa = AsyncExa("test-key", api_base=api.url)
        try:
            await exa.websets.list(limit=5, extra_query=extra_query)
        finally:
            await exa.client.aclose()

    asyncio.run(run_async())

    sync_query, async_query = (request["query"] for request in api.requests)
    assert sync_query == async_query == {"flag": ["true"], "off": ["false"], "limit": ["5"]}


def test_both_clients_encode_list_values_of_extra_query_alike(api):
    api.reply = lambda request: {"data": [], "hasMore": False}
    extra_query = {"flags": [True, False], "tags": ["a", None], "pair": ("x", True), "top": True}
    Exa("test-key", base_url=api.url).websets.list(extra_query=extra_query)

    async def run_async():
        async with AsyncExa("test-key", api_base=api.url) as exa:
            await exa.websets.list(extra_query=extra_query)

    asyncio.run(run_async())

    sync_query, async_query = (request["query"] for request in api.requests)
    assert sync_query == async_query == {
        "flags": ["true", "false"],
        "tags": ["a"],
        "pair": ["x", "true"],
        "top": ["true"],
    }


def test_sync_extra_header_set_to_none_is_skipped(api):
    Exa("test-key", base_url=api.url).search(
        "test", extra_headers={"X-API-KEY": None, "X-Trace": None}
    )
    assert api.requests[0]["headers"]["x-api-key"] == "test-key"
    assert "x-trace" not in api.requests[0]["headers"]


@pytest.mark.asyncio
async def test_async_extra_header_set_to_none_is_skipped(api):
    exa = AsyncExa("test-key", api_base=api.url)
    try:
        await exa.search("test", extra_headers={"X-API-KEY": None, "X-Trace": None})
    finally:
        await exa.client.aclose()
    assert api.requests[0]["headers"]["x-api-key"] == "test-key"
    assert "x-trace" not in api.requests[0]["headers"]


@pytest.mark.parametrize("name", ["accept", "Accept"])
def test_sync_agent_stream_keeps_its_accept_header(api, name):
    api.reply = _events_when_asked
    exa = Exa("test-key", base_url=api.url)

    events = list(
        exa.agent.runs.create(query="test", stream=True, extra_headers={name: "application/json"})
    )

    assert [event.event for event in events] == ["agent_run.created"]
    assert api.requests[0]["headers"]["accept"] == "text/event-stream"


@pytest.mark.asyncio
@pytest.mark.parametrize("name", ["accept", "Accept"])
async def test_async_agent_stream_keeps_its_accept_header(api, name):
    api.reply = _events_when_asked
    exa = AsyncExa("test-key", api_base=api.url)
    try:
        stream = await exa.agent.runs.create(
            query="test", stream=True, extra_headers={name: "application/json"}
        )
        events = [event async for event in stream]
    finally:
        await exa.client.aclose()

    assert [event.event for event in events] == ["agent_run.created"]
    assert api.requests[0]["headers"]["accept"] == "text/event-stream"


def test_request_without_extras_sends_what_it_sent_before(api):
    exa = Exa("test-key", base_url=api.url)
    exa.request("/custom", {"a": 1}, params={"ignored": "on-post"})
    assert api.requests[0]["body"] == {"a": 1}
    assert api.requests[0]["query"] == {}


def test_sync_extra_headers_replace_client_headers_whatever_their_case(api):
    exa = Exa("test-key", base_url=api.url)
    exa.search(
        "test",
        betas=["from-option"],
        extra_headers={"X-API-KEY": "other-key", "user-agent": "my-app", "exa-beta": "from-header"},
    )
    sent = api.requests[0]["all_headers"]
    assert [value for name, value in sent if name == "x-api-key"] == ["other-key"]
    assert [value for name, value in sent if name == "user-agent"] == ["my-app"]
    assert [value for name, value in sent if name == "exa-beta"] == ["from-header"]


@pytest.mark.asyncio
async def test_async_extra_headers_replace_client_headers_whatever_their_case(api):
    exa = AsyncExa("test-key", api_base=api.url)
    try:
        await exa.search(
            "test", extra_headers={"X-API-KEY": "other-key", "user-agent": "my-app"}
        )
    finally:
        await exa.client.aclose()
    sent = api.requests[0]["all_headers"]
    assert [value for name, value in sent if name == "x-api-key"] == ["other-key"]
    assert [value for name, value in sent if name == "user-agent"] == ["my-app"]


def test_extra_body_cannot_be_merged_into_a_string_payload(api):
    exa = Exa("test-key", base_url=api.url)
    with pytest.raises(TypeError, match="extra_body"):
        exa.request("/custom", '{"a": 1}', extra_body={"b": 2})
    assert api.requests == []


def test_create_and_wait_sends_extra_body_with_the_create_request_only(api):
    api.reply = lambda request: {**_RUN, "status": "running" if request["method"] == "POST" else "completed"}
    exa = Exa("test-key", base_url=api.url)

    run = exa.agent.runs.create_and_wait(query="test", poll_interval=1, **EXTRA)

    assert run.status == "completed"
    create, poll = api.requests
    assert (create["method"], poll["method"]) == ("POST", "GET")
    assert create["body"] == {"query": "test", "futureField": "new"}
    assert poll["text"] == ""
    for request in api.requests:
        assert request["headers"]["x-trace"] == "abc"
        assert request["query"]["debug"] == ["1"]


@pytest.mark.asyncio
async def test_async_sub_client_sends_the_extras(api):
    api.reply = lambda request: _RUN
    exa = AsyncExa("test-key", api_base=api.url)
    try:
        await exa.agent.runs.create(query="test", **EXTRA)
        await exa.agent.runs.get("agent_run_1", **EXTRA)
    finally:
        await exa.client.aclose()

    create, get = api.requests
    assert create["body"] == {"query": "test", "futureField": "new"}
    assert get["text"] == ""
    for request in api.requests:
        assert request["headers"]["x-trace"] == "abc"
        assert request["query"]["debug"] == ["1"]


def test_sub_client_forwards_only_the_options_that_are_set():
    client = MagicMock()
    client.request.return_value = _RUN
    runs = AgentNamespace(client).runs

    runs.get("agent_run_1", extra_headers={"X-Trace": "abc"}, extra_body=None)
    runs.get("agent_run_1")

    with_option, without = client.request.call_args_list
    assert with_option.kwargs["extra_headers"] == {"X-Trace": "abc"}
    assert "extra_body" not in with_option.kwargs
    assert not set(without.kwargs) & set(EXTRA)


def test_every_page_of_a_listing_carries_the_extras():
    client = MagicMock()
    client.request.side_effect = [
        {"data": [_RUN], "hasMore": True, "nextCursor": "next"},
        {"data": [_RUN], "hasMore": False, "nextCursor": None},
    ]
    runs = AgentNamespace(client).runs

    assert len(runs.get_all(limit=1, **EXTRA)) == 2

    assert client.request.call_count == 2
    for call in client.request.call_args_list:
        assert {name: call.kwargs[name] for name in EXTRA} == EXTRA


def test_an_unknown_keyword_is_rejected_before_any_request():
    client = MagicMock()
    runs = AgentNamespace(client).runs

    with pytest.raises(TypeError, match="extra_header"):
        runs.get("agent_run_1", extra_header={"X-Trace": "abc"})
    with pytest.raises(TypeError, match="bogus"):
        next(iter(runs.list_all(bogus=1)))
    client.request.assert_not_called()


def test_a_retrying_poll_rejects_an_unknown_keyword_instead_of_retrying_it():
    client = MagicMock()
    with pytest.raises(TypeError, match="bogus"):
        ResearchClient(client).poll_until_finished("research_1", bogus=1)
    client.request.assert_not_called()


def _two_pages_from_c1(api):
    """Answer cursor `c1` with a page that continues at `c2`, and `c2` with the last page."""

    def reply(request):
        cursor = request["query"].get("cursor", [None])[0]
        # A listing stuck on `c1` would never end; stop feeding it.
        more = cursor == "c1" and len(api.requests) < 6
        return {"data": [_RUN], "hasMore": more, "nextCursor": "c2" if more else None}

    return reply


def test_sync_extra_cursor_starts_a_listing_without_pinning_it(api):
    api.reply = _two_pages_from_c1(api)
    exa = Exa("test-key", base_url=api.url)

    runs = exa.agent.runs.get_all(extra_query={"cursor": "c1", "debug": "1"})

    assert len(runs) == 2
    assert [request["query"]["cursor"] for request in api.requests] == [["c1"], ["c2"]]
    assert [request["query"]["debug"] for request in api.requests] == [["1"], ["1"]]


@pytest.mark.asyncio
async def test_async_extra_cursor_starts_a_listing_without_pinning_it(api):
    api.reply = _two_pages_from_c1(api)
    exa = AsyncExa("test-key", api_base=api.url)
    try:
        runs = await exa.agent.runs.get_all(extra_query={"cursor": "c1", "debug": "1"})
    finally:
        await exa.client.aclose()

    assert len(runs) == 2
    assert [request["query"]["cursor"] for request in api.requests] == [["c1"], ["c2"]]
    assert [request["query"]["debug"] for request in api.requests] == [["1"], ["1"]]


def test_every_pagination_loop_drops_the_extra_cursor_after_the_first_page():
    loops = 0
    for path in Path(exa_py.__file__).parent.rglob("*.py"):
        lines = [line.strip() for line in path.read_text().splitlines()]
        for row, line in enumerate(lines):
            if line == "cursor = response.next_cursor":
                assert lines[row + 1] == "extra = options_for_next_page(extra)", (
                    f"{path.name}:{row + 1} advances a cursor that extra_query can still replace"
                )
                loops += 1
    assert loops >= 22


def test_options_for_next_page_removes_only_the_cursor():
    extra = {"extra_query": {"cursor": "c1", "debug": "1"}, "extra_headers": {"a": "b"}}
    assert options_for_next_page(extra) == {
        "extra_query": {"debug": "1"},
        "extra_headers": {"a": "b"},
    }
    assert extra["extra_query"] == {"cursor": "c1", "debug": "1"}
    unchanged = {"extra_query": {"debug": "1"}}
    assert options_for_next_page(unchanged) is unchanged


def _events_when_asked(request):
    return _EVENTS if request["headers"].get("accept") == "text/event-stream" else _RUN


@pytest.mark.parametrize("name", ["accept", "Accept", "ACCEPT"])
def test_sync_agent_stream_streams_when_extra_headers_restate_accept(api, name):
    api.reply = _events_when_asked
    exa = Exa("test-key", base_url=api.url)

    events = list(
        exa.agent.runs.create(query="test", stream=True, extra_headers={name: "text/event-stream"})
    )

    assert [event.event for event in events] == ["agent_run.created"]


@pytest.mark.asyncio
@pytest.mark.parametrize("name", ["accept", "Accept", "ACCEPT"])
async def test_async_agent_stream_streams_when_extra_headers_restate_accept(api, name):
    api.reply = _events_when_asked
    exa = AsyncExa("test-key", api_base=api.url)
    try:
        stream = await exa.agent.runs.create(
            query="test", stream=True, extra_headers={name: "text/event-stream"}
        )
        events = [event async for event in stream]
    finally:
        await exa.client.aclose()

    assert [event.event for event in events] == ["agent_run.created"]


def test_sync_extra_headers_do_not_change_how_the_response_is_read(api):
    api.reply = lambda request: _RUN
    exa = Exa("test-key", base_url=api.url)

    run = exa.agent.runs.get("agent_run_1", extra_headers={"Accept": "text/event-stream"})

    assert run.id == "agent_run_1"
    assert api.requests[0]["headers"]["accept"] == "text/event-stream"


@pytest.mark.asyncio
async def test_async_extra_headers_do_not_change_how_the_response_is_read(api):
    api.reply = lambda request: _RUN
    exa = AsyncExa("test-key", api_base=api.url)
    try:
        run = await exa.agent.runs.get(
            "agent_run_1", extra_headers={"Accept": "text/event-stream"}
        )
    finally:
        await exa.client.aclose()

    assert run.id == "agent_run_1"
    assert api.requests[0]["headers"]["accept"] == "text/event-stream"


def test_an_extra_query_holding_only_stream_adds_no_query_string(api):
    exa = Exa("test-key", base_url=api.url)
    exa.request("/custom", {"a": 1}, params={"ignored": "on-post"}, extra_query={"stream": "true"})
    assert api.requests[0]["query"] == {}


def test_sync_extra_header_replaces_every_casing_of_a_header(api):
    exa = Exa("default-key", base_url=api.url)
    exa.request(
        "/custom", {"a": 1}, headers={"X-API-KEY": "old"}, extra_headers={"X-Api-Key": "new"}
    )
    sent = api.requests[0]["all_headers"]
    assert [value for name, value in sent if name == "x-api-key"] == ["new"]


@pytest.mark.asyncio
async def test_async_extra_header_replaces_every_casing_of_a_header(api):
    exa = AsyncExa("default-key", api_base=api.url)
    try:
        await exa.async_request(
            "/custom", {"a": 1}, headers={"X-API-KEY": "old"}, extra_headers={"X-Api-Key": "new"}
        )
    finally:
        await exa.client.aclose()
    sent = api.requests[0]["all_headers"]
    assert [value for name, value in sent if name == "x-api-key"] == ["new"]


def _sub_clients(owner, seen):
    """Yield every client object reachable from `owner` that makes requests."""
    for value in vars(owner).values():
        module = type(value).__module__
        if not module.startswith("exa_py.") or id(value) in seen:
            continue
        if isinstance(value, Exa) or module.startswith("exa_py.tools"):
            continue
        seen.add(id(value))
        if hasattr(value, "request"):
            yield value
        yield from _sub_clients(value, seen)


@pytest.mark.parametrize("exa", [Exa("test-key"), AsyncExa("test-key")], ids=["sync", "async"])
def test_every_sub_client_method_accepts_the_request_options(exa):
    helpers = {"request", "build_pagination_params"}
    checked = 0
    for client in _sub_clients(exa, set()):
        for name, member in inspect.getmembers(type(client), inspect.isfunction):
            if name.startswith("_") or name in helpers:
                continue
            kinds = {p.name: p.kind for p in inspect.signature(member).parameters.values()}
            assert kinds.get("extra") is inspect.Parameter.VAR_KEYWORD, (
                f"{type(client).__name__}.{name} must take **extra: Unpack[ExtraRequestOptions] "
                "and pass it to the requests it makes"
            )
            checked += 1
    assert checked > 100


def test_given_request_options_drops_unset_options_and_rejects_unknown_names():
    assert given_request_options({"extra_headers": {"a": "b"}, "extra_body": None}) == {
        "extra_headers": {"a": "b"}
    }
    with pytest.raises(TypeError, match="unexpected keyword argument 'timeout'"):
        given_request_options({"timeout": 3})


def test_merge_headers_replaces_any_casing_and_leaves_its_input_alone():
    headers = {"x-api-key": "a", "Content-Type": "application/json"}
    assert merge_headers(headers, {"X-Api-Key": "b", "content-type": "c"}) == {
        "X-Api-Key": "b",
        "content-type": "c",
    }
    assert headers == {"x-api-key": "a", "Content-Type": "application/json"}
    assert merge_headers(headers, None) == headers
    assert merge_headers({"x-api-key": "a", "X-API-KEY": "b"}, {"X-Api-Key": "c"}) == {
        "X-Api-Key": "c"
    }
    assert merge_headers({"x-api-key": "a"}, {"X-API-KEY": None}) == {"x-api-key": "a"}
    assert merge_headers({"Accept": "text/event-stream"}, {"accept": "application/json"}) == {
        "Accept": "text/event-stream"
    }
    assert merge_headers({"Accept": "application/json"}, {"accept": "text/plain"}) == {
        "accept": "text/plain"
    }


def test_merge_query_and_merge_body():
    params = {"cursor": "c1", "limit": 5}
    assert merge_query(params, None) is params
    assert merge_query(params, {"limit": 10}) == {"cursor": "c1", "limit": 10}
    assert merge_query(None, {"debug": "1"}) == {"debug": "1"}
    assert merge_query(params, {"stream": "true"}) is params
    assert merge_query(params, {"limit": None}) is params
    assert merge_query(None, {"flag": True, "off": False}) == {"flag": "true", "off": "false"}
    assert merge_query(params, {"stream": "true", "limit": 10}) == {"cursor": "c1", "limit": 10}

    body = {"a": 1}
    assert merge_body(body, None) is body
    assert merge_body(body, {"a": 2, "stream": True}) == {"a": 2}
    assert merge_body(None, {"b": 2}) == {"b": 2}
    assert merge_body(None, {"stream": True}) is None
