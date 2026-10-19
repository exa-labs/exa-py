"""Transport timeouts surface as ExaTimeoutError and stay catchable as before.

A timeout bounds connecting and each wait for data, and a stream only until
a successful response starts: these tests run both clients against local
servers that stall, stream slower than the timeout, or answer late.
"""

import copy
import pickle
import socket
import threading
import time
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


# The clients' timeout in the streaming tests, and the gap between two events of
# a stream, longer than the timeout.
_TIMEOUT = 0.2
_GAP = 0.5


def _event(index: int) -> bytes:
    return f'data: {{"choices":[{{"delta":{{"content":"c{index}"}}}}]}}\n\n'.encode()


@pytest.fixture
def paced_server():
    """A local server whose streams are slower than `_TIMEOUT`.

    A path with ``/late`` in it gets a response that never starts; one with
    ``/error``, a 500 response whose body stalls. Any other path streams three events `_GAP`
    seconds apart: chunked on a kept-alive connection, or, under ``/close``,
    as a body that runs to the end of the connection (``Connection: close``).
    """
    release = threading.Event()

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def _handle(self):
            self.rfile.read(int(self.headers.get("Content-Length", 0)))
            if "/late" in self.path:
                release.wait()
                return
            if "/error" in self.path:
                self.send_response(500)
                self.send_header("Content-Length", "100")
                self.end_headers()
                self.wfile.write(b'{"error": ')
                self.wfile.flush()
                release.wait()
                return
            chunked = not self.path.startswith("/close/")
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            if chunked:
                self.send_header("Transfer-Encoding", "chunked")
            else:
                self.send_header("Connection", "close")
            self.end_headers()
            for index in range(3):
                if index and release.wait(_GAP):
                    return
                self._send(_event(index), chunked)
            if chunked:
                self._send(b"", chunked)

        def _send(self, data: bytes, chunked: bool) -> None:
            self.wfile.write(b"%x\r\n%s\r\n" % (len(data), data) if chunked else data)
            self.wfile.flush()

        do_GET = do_POST = _handle

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


@pytest.mark.parametrize("connection", ["", "/close"], ids=["keep-alive", "close"])
def test_a_sync_stream_is_timed_until_it_starts_only(paced_server, connection):
    exa = Exa("test-key", base_url=paced_server + connection, timeout=_TIMEOUT)
    started = time.monotonic()
    assert [chunk.content for chunk in exa.stream_answer("q")] == ["c0", "c1", "c2"]
    assert time.monotonic() - started >= 2 * _GAP

    late = Exa("test-key", base_url=paced_server + "/late", timeout=_TIMEOUT)
    with pytest.raises(ExaTimeoutError) as raised:
        late.stream_answer("q")
    assert isinstance(raised.value, requests.exceptions.ReadTimeout)


@pytest.mark.parametrize("connection", ["", "/close"], ids=["keep-alive", "close"])
@pytest.mark.parametrize("method", ["GET", "POST"])
def test_a_raw_sync_stream_is_timed_until_it_starts_only(paced_server, method, connection):
    exa = Exa("test-key", base_url=paced_server + connection, timeout=_TIMEOUT)
    if method == "GET":
        response = exa.request("/events", method="GET", params={"stream": "true"})
    else:
        response = exa.request("/events", {"stream": True})
    assert [line for line in response.iter_lines() if line] == [
        _event(index).strip() for index in range(3)
    ]

    with pytest.raises(ExaTimeoutError):
        exa.request("/late", {"stream": True})


def test_a_sync_stream_error_response_is_read_under_the_timeout(paced_server):
    exa = Exa("test-key", base_url=paced_server + "/error", timeout=_TIMEOUT)
    with pytest.raises(ExaTimeoutError):
        exa.stream_answer("q")


@pytest.mark.asyncio
@pytest.mark.parametrize("connection", ["", "/close"], ids=["keep-alive", "close"])
async def test_an_async_stream_is_timed_until_it_starts_only(paced_server, connection):
    async with AsyncExa("test-key", api_base=paced_server + connection, timeout=_TIMEOUT) as exa:
        started = time.monotonic()
        stream = await exa.stream_answer("q")
        assert [chunk.content async for chunk in stream] == ["c0", "c1", "c2"]
        assert time.monotonic() - started >= 2 * _GAP

        response = await exa.async_request("/events", method="GET", params={"stream": "true"})
        try:
            assert [line async for line in response.aiter_lines() if line] == [
                _event(index).decode().strip() for index in range(3)
            ]
        finally:
            await response.aclose()

    async with AsyncExa("test-key", api_base=paced_server + "/late", timeout=_TIMEOUT) as late:
        with pytest.raises(ExaTimeoutError) as raised:
            await late.stream_answer("q")
        assert isinstance(raised.value, httpx.ReadTimeout)


@pytest.mark.asyncio
async def test_an_async_stream_error_response_is_read_under_the_timeout(paced_server):
    async with AsyncExa("test-key", api_base=paced_server + "/error", timeout=_TIMEOUT) as exa:
        with pytest.raises(ExaTimeoutError):
            await exa.stream_answer("q")


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


# An address reserved for documentation. The `several_addresses` fixture makes a
# connection to it time out, as one to an address that drops packets does.
_BLACK_HOLE = "192.0.2.1"


@pytest.fixture
def several_addresses(monkeypatch):
    """Host names that resolve to several addresses; returns a closed local port.

    ``two-addresses.test`` resolves to an address whose connection times out,
    then to the closed port, which refuses at once. ``refusing.test`` resolves
    to the closed port twice. ``unresolvable.test`` fails its lookup after
    `_TIMEOUT` seconds.
    """
    closed = socket.socket()
    closed.bind(("127.0.0.1", 0))
    port = closed.getsockname()[1]
    closed.close()
    refused = (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", port))
    timing_out = (socket.AF_INET, socket.SOCK_STREAM, 6, "", (_BLACK_HOLE, port))
    real_getaddrinfo = socket.getaddrinfo

    def getaddrinfo(host, *args, **kwargs):
        if host == "two-addresses.test":
            return [timing_out, refused]
        if host == "refusing.test":
            return [refused, refused]
        if host == "unresolvable.test":
            time.sleep(_TIMEOUT)
            raise socket.gaierror(socket.EAI_NONAME, "Name or service not known")
        return real_getaddrinfo(host, *args, **kwargs)

    class Socket(socket.socket):
        def connect(self, address):
            if address[0] == _BLACK_HOLE:
                time.sleep(self.gettimeout())
                raise socket.timeout("timed out")
            return super().connect(address)

    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)
    monkeypatch.setattr(socket, "socket", Socket)
    return port


def test_a_connect_timeout_on_one_of_several_addresses_is_typed(several_addresses):
    exa = Exa("test-key", base_url=f"http://two-addresses.test:{several_addresses}", timeout=_TIMEOUT)
    with pytest.raises(ExaTimeoutError) as raised:
        exa.search("q")
    assert isinstance(raised.value, requests.exceptions.ConnectTimeout)
    assert isinstance(raised.value, requests.exceptions.ConnectionError)
    assert "connect timeout=0.2" in str(raised.value)
    assert type(raised.value.__cause__.__cause__) is requests.exceptions.ConnectionError


@pytest.mark.parametrize("host", ["refusing.test", "unresolvable.test"])
def test_a_refused_connection_or_failed_lookup_stays_a_connection_error(several_addresses, host):
    exa = Exa("test-key", base_url=f"http://{host}:{several_addresses}", timeout=_TIMEOUT)
    with pytest.raises(requests.exceptions.ConnectionError) as raised:
        exa.search("q")
    assert not isinstance(raised.value, (ExaTimeoutError, requests.exceptions.Timeout))


def test_an_import_upload_connect_timeout_on_one_of_several_addresses_is_typed(several_addresses):
    client = ImportsClient(Exa("test-key", timeout=_TIMEOUT))
    created = {**_IMPORT, "uploadUrl": f"http://two-addresses.test:{several_addresses}/upload"}
    with patch.object(client, "request", return_value=created):
        with pytest.raises(ExaTimeoutError) as raised:
            client.create({}, csv_data="url\nhttps://example.com")
    assert isinstance(raised.value, requests.exceptions.ConnectTimeout)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "timeout_class,setting",
    [
        (httpx.ConnectTimeout, "connect"),
        (httpx.ReadTimeout, "read"),
        (httpx.WriteTimeout, "write"),
        (httpx.PoolTimeout, "pool"),
    ],
)
async def test_an_httpx_timeout_without_a_message_is_given_one(timeout_class, setting):
    def handle(request: httpx.Request) -> httpx.Response:
        raise timeout_class("", request=request)

    exa = AsyncExa("test-key", timeout=5)
    exa._client = httpx.AsyncClient(transport=httpx.MockTransport(handle), timeout=exa.timeout)
    try:
        with pytest.raises(ExaTimeoutError) as raised:
            await exa.search("slow")
    finally:
        await exa.aclose()
    assert str(raised.value) == f"{setting.capitalize()} timed out. ({setting} timeout=5)"
    assert isinstance(raised.value, timeout_class)
    assert raised.value.request.url.path == "/search"
    assert str(raised.value.__cause__) == ""


def test_a_timeout_without_a_message_or_a_request_is_still_described():
    assert str(_as_exa_timeout(httpx.ReadTimeout(""))) == "Read timed out."
    assert str(_as_exa_timeout(requests.exceptions.ReadTimeout())) == "Request timed out."


@pytest.mark.asyncio
async def test_an_async_tool_hands_the_model_the_timeout_message():
    def handle(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("", request=request)

    exa = AsyncExa("test-key", timeout=5)
    exa._client = httpx.AsyncClient(transport=httpx.MockTransport(handle), timeout=exa.timeout)
    exa.openai.web_search()
    message = {
        "role": "assistant",
        "tool_calls": [
            {"id": "c1", "type": "function", "function": {"name": "web_search", "arguments": '{"query": "q"}'}}
        ],
    }
    try:
        outputs = await exa.openai.handle_tool_calls(message)
    finally:
        await exa.aclose()
    assert outputs == [
        {"role": "tool", "tool_call_id": "c1", "content": "Error: Read timed out. (read timeout=5)"}
    ]


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
