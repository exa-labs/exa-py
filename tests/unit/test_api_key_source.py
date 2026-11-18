"""``api_key`` given as a function, on ``Exa`` and ``AsyncExa``.

Runs against a local server, so each test sees the ``x-api-key`` every request
carried and whether a request was sent at all.
"""

import asyncio
import inspect
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx
import pytest
import requests

from exa_py import AsyncExa, Exa, ExaTimeoutError

BAD_KEYS = [
    pytest.param("", id="an empty string"),
    pytest.param("tok 1", id="an inner space"),
    pytest.param("\ufefftok-1", id="a leading U+FEFF"),
    pytest.param("tok-1\n", id="a trailing newline"),
    pytest.param("t\u00f6k-1", id="a non-ASCII letter"),
    pytest.param("tok-1\x7f", id="U+007F"),
    pytest.param(None, id="None"),
    pytest.param(42, id="a number"),
]
BAD_KEY_MESSAGE = "api_key must return a non-empty string of visible ASCII characters"
# Every character from U+0021 to U+007E, in order.
EVERY_VISIBLE_ASCII = "".join(chr(code) for code in range(0x21, 0x7F))
# What an api_key function might raise, transport timeouts included.
KEY_FUNCTION_ERRORS = [
    pytest.param(lambda: RuntimeError("no key"), id="RuntimeError"),
    pytest.param(
        lambda: requests.exceptions.ReadTimeout("the key store timed out"),
        id="requests ReadTimeout",
    ),
    pytest.param(lambda: httpx.ReadTimeout("the key store timed out"), id="httpx ReadTimeout"),
    pytest.param(lambda: TimeoutError("the key store timed out"), id="TimeoutError"),
]
IMPORT_PARAMS = {"format": "csv", "entity": {"type": "company"}, "count": 1, "size": 10}


class _Api:
    """A local server that records the headers of every request and answers with an empty search response."""

    def __init__(self):
        self.requests = []
        # Seconds each response waits, so that a request times out.
        self.stall = 0
        self._closed = threading.Event()
        api = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length", 0))
                self.rfile.read(length)
                api.requests.append({name.lower(): value for name, value in self.headers.items()})
                if api.stall:
                    api._closed.wait(api.stall)
                payload = b'{"results": [], "citations": [], "answer": "ok"}'
                try:
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                except OSError:
                    # The client stopped waiting for a stalled response.
                    pass

            def log_message(self, *args):
                pass

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._server.daemon_threads = True
        self.url = f"http://127.0.0.1:{self._server.server_address[1]}"
        # A short poll interval keeps close() from waiting half a second.
        threading.Thread(
            target=self._server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True
        ).start()

    @property
    def keys(self):
        """The ``x-api-key`` of each request received, in order, or None where it had none."""
        return [headers.get("x-api-key") for headers in self.requests]

    def close(self):
        self._closed.set()
        self._server.shutdown()
        self._server.server_close()


@pytest.fixture
def api():
    server = _Api()
    try:
        yield server
    finally:
        server.close()


@pytest.fixture(autouse=True)
def no_key_in_environment(monkeypatch):
    # A key in the environment must not stand in for the function.
    monkeypatch.delenv("EXA_API_KEY", raising=False)


def _source(keys, asynchronous=False):
    """Return a function, or a coroutine function, that returns the next of ``keys`` and records each call."""
    keys = iter(keys)

    def api_key():
        api_key.calls += 1
        return next(keys)

    async def async_api_key():
        async_api_key.calls += 1
        return next(keys)

    source = async_api_key if asynchronous else api_key
    source.calls = 0
    return source


def _failing(error, asynchronous=False):
    """Return a function, or a coroutine function, that raises ``error``."""

    def api_key():
        raise error

    async def async_api_key():
        raise error

    return async_api_key if asynchronous else api_key


def _returning(value, asynchronous=False):
    """Return a function, or a coroutine function, that returns ``value``."""

    def api_key():
        return value

    async def async_api_key():
        return value

    return async_api_key if asynchronous else api_key


ASYNC_SOURCES = pytest.mark.parametrize(
    "asynchronous", [False, True], ids=["function", "coroutine function"]
)


def test_exa_calls_the_function_before_each_request_and_sends_each_key(api):
    source = _source(["tok-1", "tok-2"])
    exa = Exa(api_key=source, base_url=api.url)

    exa.search("first")
    exa.search("second")

    assert not any(name.lower() == "x-api-key" for name in exa.headers)
    assert source.calls == 2
    assert api.keys == ["tok-1", "tok-2"]


@ASYNC_SOURCES
async def test_async_exa_calls_the_function_before_each_request_and_sends_each_key(api, asynchronous):
    source = _source(["tok-1", "tok-2"], asynchronous)

    async with AsyncExa(api_key=source, base_url=api.url) as exa:
        await exa.search("first")
        await exa.search("second")

    assert source.calls == 2
    assert api.keys == ["tok-1", "tok-2"]


async def test_async_exa_calls_the_function_once_for_each_of_several_concurrent_requests(api):
    calls = []

    async def api_key():
        calls.append(None)
        key = f"tok-{len(calls)}"
        # Every call is still pending when the next request asks for a key.
        await asyncio.sleep(0.01)
        return key

    async with AsyncExa(api_key=api_key, base_url=api.url) as exa:
        await asyncio.gather(*(exa.search(f"query {index}") for index in range(5)))

    assert len(calls) == 5
    assert sorted(api.keys) == ["tok-1", "tok-2", "tok-3", "tok-4", "tok-5"]


async def _search(exa, **options):
    return await exa.search("query", **options)


async def _stream_search(exa, **options):
    return [chunk async for chunk in await exa.stream_search("query", **options)]


async def _create_import(exa):
    return await exa.websets.imports.create(IMPORT_PARAMS)


@pytest.mark.parametrize("make_error", KEY_FUNCTION_ERRORS)
@pytest.mark.parametrize(
    "call",
    [
        pytest.param(lambda exa: exa.search("query"), id="search"),
        pytest.param(lambda exa: list(exa.stream_search("query")), id="stream_search"),
        pytest.param(lambda exa: exa.websets.imports.create(IMPORT_PARAMS), id="imports.create"),
    ],
)
def test_exa_raises_what_the_function_raises_and_sends_nothing(api, call, make_error):
    error = make_error()
    exa = Exa(api_key=_failing(error), base_url=api.url)

    with pytest.raises(type(error)) as raised:
        call(exa)

    assert raised.value is error
    assert api.requests == []


@ASYNC_SOURCES
@pytest.mark.parametrize("make_error", KEY_FUNCTION_ERRORS)
@pytest.mark.parametrize(
    "call",
    [
        pytest.param(_search, id="search"),
        pytest.param(_stream_search, id="stream_search"),
        pytest.param(_create_import, id="imports.create"),
    ],
)
async def test_async_exa_raises_what_the_function_raises_and_sends_nothing(
    api, call, make_error, asynchronous
):
    error = make_error()
    async with AsyncExa(api_key=_failing(error, asynchronous), base_url=api.url) as exa:
        with pytest.raises(type(error)) as raised:
            await call(exa)

    assert raised.value is error
    assert api.requests == []


@pytest.mark.parametrize(
    "call",
    [
        pytest.param(lambda exa: exa.search("query", timeout=0.05), id="search"),
        pytest.param(lambda exa: list(exa.stream_search("query", timeout=0.05)), id="stream_search"),
    ],
)
def test_exa_raises_exa_timeout_error_when_the_request_itself_times_out(api, call):
    api.stall = 5
    source = _source(["tok-1"])
    exa = Exa(api_key=source, base_url=api.url)

    with pytest.raises(ExaTimeoutError):
        call(exa)

    assert source.calls == 1


@ASYNC_SOURCES
@pytest.mark.parametrize(
    "call",
    [pytest.param(_search, id="search"), pytest.param(_stream_search, id="stream_search")],
)
async def test_async_exa_raises_exa_timeout_error_when_the_request_itself_times_out(
    api, call, asynchronous
):
    api.stall = 5
    source = _source(["tok-1"], asynchronous)

    async with AsyncExa(api_key=source, base_url=api.url) as exa:
        with pytest.raises(ExaTimeoutError):
            await call(exa, timeout=0.05)

    assert source.calls == 1


def test_exa_sends_the_key_on_a_streaming_call(api):
    exa = Exa(api_key=_returning("tok-1"), base_url=api.url)

    list(exa.stream_search("query"))

    assert api.keys == ["tok-1"]


@ASYNC_SOURCES
async def test_async_exa_sends_the_key_on_a_streaming_call(api, asynchronous):
    async with AsyncExa(api_key=_returning("tok-1", asynchronous), base_url=api.url) as exa:
        await _stream_search(exa)

    assert api.keys == ["tok-1"]


@pytest.mark.parametrize("returned", BAD_KEYS)
def test_exa_refuses_a_value_that_is_not_a_key_and_sends_nothing(api, returned):
    exa = Exa(api_key=_returning(returned), base_url=api.url)

    with pytest.raises(TypeError, match=BAD_KEY_MESSAGE):
        exa.search("query")

    assert api.requests == []


@ASYNC_SOURCES
@pytest.mark.parametrize("returned", BAD_KEYS)
async def test_async_exa_refuses_a_value_that_is_not_a_key_and_sends_nothing(api, returned, asynchronous):
    async with AsyncExa(api_key=_returning(returned, asynchronous), base_url=api.url) as exa:
        with pytest.raises(TypeError, match=BAD_KEY_MESSAGE):
            await exa.search("query")

    assert api.requests == []


def test_exa_sends_a_key_of_every_visible_ascii_character_as_it_is(api):
    exa = Exa(api_key=_returning(EVERY_VISIBLE_ASCII), base_url=api.url)

    exa.search("query")

    assert api.keys == [EVERY_VISIBLE_ASCII]


@ASYNC_SOURCES
async def test_async_exa_sends_a_key_of_every_visible_ascii_character_as_it_is(api, asynchronous):
    async with AsyncExa(api_key=_returning(EVERY_VISIBLE_ASCII, asynchronous), base_url=api.url) as exa:
        await exa.search("query")

    assert api.keys == [EVERY_VISIBLE_ASCII]


@pytest.mark.parametrize(
    "call",
    [
        pytest.param(
            lambda exa: exa.request("/search", {"query": "query"}, headers={"X-Api-Key": "explicit"}),
            id="headers",
        ),
        pytest.param(
            lambda exa: exa.search("query", extra_headers={"X-API-KEY": "explicit"}),
            id="extra_headers",
        ),
    ],
)
def test_exa_sends_the_x_api_key_a_call_sets_without_calling_the_function(api, call):
    source = _source(["from-function"])
    exa = Exa(api_key=source, base_url=api.url)

    call(exa)

    assert source.calls == 0
    assert api.keys == ["explicit"]


@ASYNC_SOURCES
@pytest.mark.parametrize(
    "call",
    [
        pytest.param(
            lambda exa: exa.async_request("/search", {"query": "query"}, headers={"X-Api-Key": "explicit"}),
            id="headers",
        ),
        pytest.param(
            lambda exa: exa.search("query", extra_headers={"X-API-KEY": "explicit"}),
            id="extra_headers",
        ),
    ],
)
async def test_async_exa_sends_the_x_api_key_a_call_sets_without_calling_the_function(api, call, asynchronous):
    source = _source(["from-function"], asynchronous)

    async with AsyncExa(api_key=source, base_url=api.url) as exa:
        await call(exa)

    assert source.calls == 0
    assert api.keys == ["explicit"]


def test_exa_calls_the_function_when_extra_headers_set_x_api_key_to_none(api):
    # A header set to None in extra_headers is skipped, so it removes nothing.
    source = _source(["from-function"])
    exa = Exa(api_key=source, base_url=api.url)

    exa.search("query", extra_headers={"x-api-key": None})

    assert source.calls == 1
    assert api.keys == ["from-function"]


@pytest.mark.parametrize(
    "client_timeout, call_timeout",
    [(0.05, None), (None, 0.05)],
    ids=["client timeout", "call timeout"],
)
async def test_async_exa_bounds_the_wait_for_a_coroutine_function_with_the_timeout(
    api, client_timeout, call_timeout
):
    cancelled = asyncio.Event()

    async def api_key():
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            cancelled.set()
            raise
        return "too-late"

    async with AsyncExa(api_key=api_key, base_url=api.url, timeout=client_timeout) as exa:
        with pytest.raises(ExaTimeoutError) as raised:
            await exa.search("query", timeout=call_timeout)

    assert isinstance(raised.value, httpx.TimeoutException)
    await asyncio.wait_for(cancelled.wait(), timeout=1)
    assert api.requests == []


def test_exa_refuses_a_coroutine_function_when_constructed():
    async def api_key():
        return "tok-1"

    with pytest.raises(TypeError, match="Use AsyncExa"):
        Exa(api_key=api_key)


def test_exa_refuses_a_function_that_returns_an_awaitable_and_closes_it(api):
    async def read_key():
        return "tok-1"

    coroutines = []

    def api_key():
        coroutines.append(read_key())
        return coroutines[-1]

    exa = Exa(api_key=api_key, base_url=api.url)

    with pytest.raises(TypeError, match="Use AsyncExa"):
        exa.search("query")

    assert len(coroutines) == 1
    assert inspect.getcoroutinestate(coroutines[0]) == inspect.CORO_CLOSED
    assert api.requests == []


def test_async_exa_request_names_async_request_for_an_awaitable_key(api):
    async def api_key():
        return "tok-1"

    exa = AsyncExa(api_key=api_key, base_url=api.url)

    with pytest.raises(TypeError) as raised:
        exa.request("/search", {"query": "query"})

    assert "async_request" in str(raised.value)
    assert "Use AsyncExa" not in str(raised.value)
    assert api.requests == []
