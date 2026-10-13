"""Transport timeouts surface as ExaTimeoutError and stay catchable as before."""

import copy
import pickle
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import Mock, patch

import httpx
import pytest
import requests
from urllib3.exceptions import ReadTimeoutError

from exa_py import AsyncExa, Exa, ExaTimeoutError
from exa_py.agent.utils import async_stream_agent_events, stream_agent_events
from exa_py.errors import _as_exa_timeout, typed_timeouts
from exa_py.research.utils import async_stream_sse_events, stream_sse_events
from exa_py.websets.imports.client import ImportsClient

_FIRST_CHUNK = b'data: {"choices":[{"delta":{"content":"first"}}]}\n'
_IMPORT = {
    "id": "imp_1", "object": "import", "status": "pending", "format": "csv",
    "title": "test", "count": 1, "metadata": {},
    "createdAt": "2026-01-01T00:00:00Z", "updatedAt": "2026-01-01T00:00:00Z",
    "uploadUrl": "https://example.com/upload", "uploadValidUntil": "2026-01-01T01:00:00Z",
}


@pytest.fixture
def stalling_server():
    """A local server that never finishes a response.

    A request whose body asks for a stream gets headers and one chunk; any
    other request gets nothing. Both then hang until the test ends.
    """
    release = threading.Event()

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            if b'"stream": true' in body or b'"stream":true' in body:
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.end_headers()
                self.wfile.write(_FIRST_CHUNK)
                self.wfile.flush()
            release.wait()

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        release.set()
        server.shutdown()
        server.server_close()


def test_sync_timeout_is_typed_and_still_a_requests_timeout(stalling_server):
    exa = Exa("test-key", base_url=stalling_server, timeout=0.2)
    with pytest.raises(ExaTimeoutError) as raised:
        exa.search("slow")
    assert isinstance(raised.value, requests.exceptions.ReadTimeout)
    assert isinstance(raised.value.__cause__, requests.exceptions.ReadTimeout)
    assert not isinstance(raised.value.__cause__, ExaTimeoutError)
    assert str(raised.value) == str(raised.value.__cause__)

    with pytest.raises(requests.exceptions.Timeout):
        exa.search("slow", timeout=0.1)


def test_sync_stream_timeout_is_typed_and_still_a_connection_error(stalling_server):
    exa = Exa("test-key", base_url=stalling_server, timeout=0.2)
    stream = exa.stream_answer("slow")  # Headers arrive; the body then stalls.
    with pytest.raises(ExaTimeoutError) as raised:
        list(stream)
    assert isinstance(raised.value, requests.exceptions.ConnectionError)


def test_a_raw_streamed_response_raises_the_transport_error_as_is(stalling_server):
    exa = Exa("test-key", base_url=stalling_server, timeout=0.2)
    response = exa.request("/search", {"stream": True})
    with pytest.raises(requests.exceptions.ConnectionError) as raised:
        list(response.iter_lines())
    assert not isinstance(raised.value, ExaTimeoutError)


@pytest.mark.asyncio
async def test_async_timeout_is_typed_and_still_an_httpx_timeout(stalling_server):
    exa = AsyncExa("test-key", api_base=stalling_server, timeout=0.2)
    try:
        with pytest.raises(ExaTimeoutError) as raised:
            await exa.search("slow")
        assert isinstance(raised.value, httpx.ReadTimeout)
        assert isinstance(raised.value.__cause__, httpx.ReadTimeout)
        assert raised.value.request.url.path == "/search"

        with pytest.raises(httpx.TimeoutException):
            await exa.search("slow", timeout=0.1)
    finally:
        await exa.client.aclose()


@pytest.mark.asyncio
async def test_async_stream_timeout_is_typed_and_closes_the_response(stalling_server):
    exa = AsyncExa("test-key", api_base=stalling_server, timeout=0.2)
    try:
        stream = await exa.stream_answer("slow")
        chunks = stream.__aiter__()
        assert (await chunks.__anext__()).content == "first"
        with pytest.raises(ExaTimeoutError) as raised:
            await chunks.__anext__()
        assert isinstance(raised.value, httpx.ReadTimeout)
        assert stream._raw_response.is_closed
    finally:
        await exa.client.aclose()


@pytest.mark.parametrize(
    "transport_error",
    [
        requests.exceptions.ConnectTimeout("connect timed out"),
        requests.exceptions.ReadTimeout("read timed out"),
        requests.exceptions.ConnectionError(ReadTimeoutError(None, None, "Read timed out.")),
    ],
)
def test_every_requests_timeout_keeps_its_own_class(transport_error):
    exa = Exa("test-key")
    with patch("exa_py.api.requests.post", side_effect=transport_error):
        with pytest.raises(ExaTimeoutError) as raised:
            exa.search("slow")
    assert isinstance(raised.value, type(transport_error))
    assert raised.value.args == transport_error.args
    assert raised.value.__cause__ is transport_error


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "timeout_class",
    [httpx.ConnectTimeout, httpx.ReadTimeout, httpx.WriteTimeout, httpx.PoolTimeout],
)
async def test_every_httpx_timeout_keeps_its_own_class(timeout_class):
    def handle(request: httpx.Request) -> httpx.Response:
        raise timeout_class("timed out", request=request)

    exa = AsyncExa("test-key")
    exa._client = httpx.AsyncClient(transport=httpx.MockTransport(handle))
    try:
        with pytest.raises(ExaTimeoutError) as raised:
            await exa.get_contents("https://example.com")
        assert isinstance(raised.value, timeout_class)
        assert str(raised.value) == "timed out"
    finally:
        await exa._client.aclose()


def test_other_failures_are_left_as_they_are():
    exa = Exa("test-key")
    refused = requests.exceptions.ConnectionError("connection refused")
    with patch("exa_py.api.requests.post", side_effect=refused):
        with pytest.raises(requests.exceptions.ConnectionError) as raised:
            exa.search("down")
    assert raised.value is refused

    response = requests.Response()
    response.status_code = 404
    response._content = b"not found"
    with patch("exa_py.api.requests.post", return_value=response):
        with pytest.raises(ValueError, match="status code 404"):
            exa.search("missing")


def test_a_typed_timeout_is_not_wrapped_twice():
    @typed_timeouts
    def outer():
        return inner()

    @typed_timeouts
    def inner():
        raise requests.exceptions.ReadTimeout("read timed out")

    with pytest.raises(ExaTimeoutError) as raised:
        outer()
    assert type(raised.value.__cause__) is requests.exceptions.ReadTimeout


def test_a_typed_timeout_survives_pickling_and_copying():
    request = httpx.Request("POST", "https://api.exa.ai/search")
    for transport_error in (
        requests.exceptions.ReadTimeout("read timed out"),
        requests.exceptions.ConnectionError(ReadTimeoutError(None, None, "Read timed out.")),
        httpx.ReadTimeout("read timed out", request=request),
    ):
        typed = _as_exa_timeout(transport_error)
        for round_trip in (lambda error: pickle.loads(pickle.dumps(error)), copy.copy):
            clone = round_trip(typed)
            assert isinstance(clone, ExaTimeoutError)
            assert isinstance(clone, type(transport_error))
            assert type(clone) is type(typed)
            # Carries whatever the transport error itself keeps across the trip.
            assert str(clone) == str(round_trip(transport_error))

    restored = pickle.loads(pickle.dumps(_as_exa_timeout(httpx.ReadTimeout("slow", request=request))))
    assert restored.request.url == request.url


def test_sync_event_streams_type_a_timeout_between_events():
    def lines():
        yield b"event: first"
        yield b'data: {"n": 1}'
        yield b""
        raise requests.exceptions.ConnectionError(ReadTimeoutError(None, None, "Read timed out."))

    for stream in (stream_agent_events, stream_sse_events):
        response = Mock()
        response.iter_lines.return_value = lines()
        with pytest.raises(ExaTimeoutError):
            list(stream(response))


@pytest.mark.asyncio
async def test_async_event_streams_type_a_timeout_between_events():
    class Response:
        async def aiter_lines(self):
            yield "event: first"
            yield 'data: {"n": 1}'
            yield ""
            raise httpx.ReadTimeout("read timed out")

    for stream in (async_stream_agent_events, async_stream_sse_events):
        with pytest.raises(ExaTimeoutError) as raised:
            async for _ in stream(Response()):
                pass
        assert isinstance(raised.value, httpx.ReadTimeout)


def test_import_upload_timeout_is_typed():
    client = ImportsClient(Exa("test-key", timeout=8))
    upload_timeout = requests.exceptions.ReadTimeout("upload timed out")
    with patch.object(client, "request", return_value=_IMPORT), patch(
        "exa_py.websets.imports.client.requests.put", side_effect=upload_timeout
    ):
        with pytest.raises(ExaTimeoutError) as raised:
            client.create({}, csv_data="url\nhttps://example.com")
    assert raised.value.__cause__ is upload_timeout
