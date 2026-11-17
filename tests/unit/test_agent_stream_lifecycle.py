"""Agent streams own their HTTP response before the first event is read."""

import asyncio
from collections.abc import AsyncGenerator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from pydantic import ValidationError

from exa_py import AsyncExa
from exa_py.agent import AsyncAgentNamespace, AsyncBetaClient
from exa_py.agent.utils import async_stream_agent_events
from exa_py.errors import ExaTimeoutError


class Body(httpx.AsyncByteStream):
    def __init__(self, chunks=(), error=None, wait=False):
        self.chunks = chunks
        self.error = error
        self.wait = wait
        self.reads = 0
        self.closes = 0
        self.waiting = asyncio.Event()

    async def __aiter__(self):
        self.reads += 1
        for chunk in self.chunks:
            yield chunk
        if self.wait:
            self.waiting.set()
            await asyncio.Event().wait()
        if self.error:
            raise self.error

    async def aclose(self):
        self.closes += 1


def response_for(body):
    return httpx.Response(200, stream=body)


@pytest.mark.asyncio
@pytest.mark.parametrize("beta", [False, True])
async def test_unread_create_closes_response_without_reading(beta):
    body = Body(wait=True)
    response = response_for(body)
    client = SimpleNamespace(async_request=AsyncMock(return_value=response))
    runs = (AsyncBetaClient(client).agent if beta else AsyncAgentNamespace(client)).runs
    events = await runs.create(query="local", stream=True)

    assert client.async_request.await_count == 1
    assert isinstance(events, AsyncGenerator)
    assert events.__aiter__() is events
    assert body.reads == 0
    await events.aclose()
    await events.aclose()
    assert response.is_closed
    assert body.closes == 1
    assert body.reads == 0
    with pytest.raises(StopAsyncIteration):
        await events.__anext__()


@pytest.mark.asyncio
@pytest.mark.parametrize("error", [httpx.ReadError("close failed"), httpx.ReadTimeout("close timed out")])
async def test_unread_close_preserves_transport_error_and_timeout_alias(error):
    class FailingCloseBody(Body):
        async def aclose(self):
            raise error

    body = FailingCloseBody()
    events = async_stream_agent_events(response_for(body))
    with pytest.raises(type(error)) as raised:
        await events.aclose()
    if isinstance(error, httpx.ReadTimeout):
        assert isinstance(raised.value, ExaTimeoutError)
        assert raised.value.__cause__ is error
    else:
        assert raised.value is error
    assert body.reads == 0


@pytest.mark.asyncio
async def test_started_close_and_async_generator_protocol():
    body = Body([b'event: first\ndata: {"n": 1}\n\nevent: second\ndata: text\n\n'])
    events = async_stream_agent_events(response_for(body))
    assert (await events.asend(None)).data == {"n": 1}
    assert (await events.__anext__()).data == {"value": "text"}
    error = RuntimeError("caller stopped")
    with pytest.raises(RuntimeError) as raised:
        await events.athrow(error)
    assert raised.value is error
    assert body.closes == 1
    await events.aclose()
    assert body.closes == 1


@pytest.mark.asyncio
async def test_throw_before_iteration_closes_without_reading():
    body = Body(wait=True)
    events = async_stream_agent_events(response_for(body))
    error = ValueError("caller stopped")
    with pytest.raises(ValueError) as raised:
        await events.athrow(error)
    assert raised.value is error
    assert body.closes == 1
    assert body.reads == 0


@pytest.mark.asyncio
async def test_invalid_generator_commands_leave_stream_usable():
    body = Body([b'event: first\ndata: {}\n\n'])
    events = async_stream_agent_events(response_for(body))
    with pytest.raises(TypeError):
        await events.asend(1)
    with pytest.raises(TypeError):
        await events.athrow("not an exception")
    assert body.closes == 0
    assert (await events.__anext__()).event == "first"
    await events.aclose()
    assert body.closes == 1


@pytest.mark.asyncio
async def test_exhaustion_parses_multiline_and_trailing_event_and_closes():
    body = Body([b': comment\n\nid: 7\nevent: result\ndata: {\ndata: "n": 1}\n\n', b'event: last\ndata: {}'])
    events = async_stream_agent_events(response_for(body))
    parsed = [event async for event in events]
    assert [(event.id, event.event, event.data) for event in parsed] == [
        ("7", "result", {"n": 1}), (None, "last", {})
    ]
    assert body.closes == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("error", [httpx.ReadError("read failed"), httpx.ReadTimeout("read timed out")])
async def test_read_failure_closes_and_preserves_timeout_alias(error):
    body = Body([b'event: first\ndata: {}\n\n'], error=error)
    events = async_stream_agent_events(response_for(body))
    assert (await events.__anext__()).event == "first"
    with pytest.raises(type(error)) as raised:
        await events.__anext__()
    if isinstance(error, httpx.ReadTimeout):
        assert isinstance(raised.value, ExaTimeoutError)
        assert raised.value.__cause__ is error
    else:
        assert raised.value is error
    assert body.closes == 1


@pytest.mark.asyncio
async def test_parse_failure_closes_response():
    body = Body([b'event: invalid\ndata: []\n\n'])
    with pytest.raises(ValidationError):
        await async_stream_agent_events(response_for(body)).__anext__()
    assert body.closes == 1


@pytest.mark.asyncio
async def test_cancelled_read_closes_response():
    body = Body(wait=True)
    events = async_stream_agent_events(response_for(body))
    reading = asyncio.create_task(events.__anext__())
    await asyncio.wait_for(body.waiting.wait(), 1)
    reading.cancel()
    with pytest.raises(asyncio.CancelledError):
        await reading
    assert body.closes == 1
    await events.aclose()
    assert body.closes == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("started", [False, True])
async def test_public_stream_close_releases_live_connection(started):
    peer_closed = threading.Event()

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args):
            pass

        def do_POST(self):
            self.rfile.read(int(self.headers.get("Content-Length", "0")))
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            frame = b'event: run.created\ndata: {"id":"local"}\n\n'
            self.wfile.write(("%x\r\n" % len(frame)).encode() + frame + b"\r\n")
            self.wfile.flush()
            self.connection.settimeout(2)
            try:
                if self.rfile.read(1) == b"":
                    peer_closed.set()
            except (ConnectionResetError, BrokenPipeError):
                peer_closed.set()
            except TimeoutError:
                pass
            finally:
                self.close_connection = True

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        async with AsyncExa("local-only", api_base="http://127.0.0.1:%d" % server.server_port) as client:
            events = await client.agent.runs.create(query="local", stream=True)
            if started:
                assert (await events.__anext__()).event == "run.created"
            await events.aclose()
            assert await asyncio.to_thread(peer_closed.wait, 1), "Server did not observe connection closure"
    finally:
        await asyncio.to_thread(server.shutdown)
        server.server_close()
        thread.join(2)
