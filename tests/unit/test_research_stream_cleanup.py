"""Research event streams own their response while they are being consumed."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
import requests

from exa_py.research import utils
from exa_py.research.async_client import AsyncResearchClient
from exa_py.research.sync_client import ResearchClient


EVENT_LINES = [
    "event: research-definition",
    "data: "
    + json.dumps(
        {"researchId": "research_123", "createdAt": 1, "instructions": "Find sources"}
    ),
]
STREAM_CASES = [
    ([], 0),
    (EVENT_LINES + [""], 1),
    (EVENT_LINES, 1),
    (["event: unknown", "data: {}", ""], 0),
]


def sync_response(lines):
    response = MagicMock(spec=requests.Response)
    response.iter_lines.return_value = iter(line.encode("utf-8") for line in lines)
    return response


def async_response(lines):
    response = MagicMock(spec=httpx.Response)
    response.aclose = AsyncMock()

    async def iterate():
        for line in lines:
            yield line

    response.aiter_lines.return_value = iterate()
    return response


@pytest.mark.parametrize("lines,count", STREAM_CASES)
def test_sync_closes_after_exhaustion(lines, count):
    response = sync_response(lines)
    events = list(utils.stream_sse_events(response))
    assert len(events) == count
    if events:
        assert events[0].research_id == "research_123"
    response.close.assert_called_once_with()


@pytest.mark.asyncio
@pytest.mark.parametrize("lines,count", STREAM_CASES)
async def test_async_closes_after_exhaustion(lines, count):
    response = async_response(lines)
    events = [event async for event in utils.async_stream_sse_events(response)]
    assert len(events) == count
    if events:
        assert events[0].research_id == "research_123"
    response.aclose.assert_awaited_once_with()


@pytest.mark.parametrize("after_event", [False, True])
def test_sync_read_failure_closes_and_propagates(after_event):
    response = sync_response([])
    failure = requests.exceptions.ConnectionError("stream interrupted")

    def iterate():
        if after_event:
            yield from (line.encode("utf-8") for line in EVENT_LINES + [""])
        raise failure

    response.iter_lines.return_value = iterate()
    stream = utils.stream_sse_events(response)
    if after_event:
        assert next(stream).research_id == "research_123"
    with pytest.raises(requests.exceptions.ConnectionError) as exc:
        list(stream)
    assert exc.value is failure
    response.close.assert_called_once_with()


@pytest.mark.asyncio
@pytest.mark.parametrize("after_event", [False, True])
async def test_async_read_failure_closes_and_propagates(after_event):
    response = async_response([])
    failure = httpx.ReadError("stream interrupted")

    async def iterate():
        if after_event:
            for line in EVENT_LINES + [""]:
                yield line
        raise failure

    response.aiter_lines.return_value = iterate()
    stream = utils.async_stream_sse_events(response)
    if after_event:
        assert (await stream.__anext__()).research_id == "research_123"
    with pytest.raises(httpx.ReadError) as exc:
        await stream.__anext__()
    assert exc.value is failure
    response.aclose.assert_awaited_once_with()


def test_sync_decoding_failure_closes():
    response = sync_response([])
    response.iter_lines.return_value = iter([b"\xff"])
    with pytest.raises(UnicodeDecodeError):
        list(utils.stream_sse_events(response))
    response.close.assert_called_once_with()


def test_sync_parser_failure_closes(monkeypatch):
    response = sync_response(EVENT_LINES + [""])
    failure = RuntimeError("parser interrupted")
    parser = MagicMock(side_effect=failure)
    monkeypatch.setattr(utils, "parse_research_event", parser)
    with pytest.raises(RuntimeError) as exc:
        list(utils.stream_sse_events(response))
    assert exc.value is failure
    response.close.assert_called_once_with()


@pytest.mark.asyncio
async def test_async_parser_failure_closes(monkeypatch):
    response = async_response(EVENT_LINES + [""])
    failure = RuntimeError("parser interrupted")
    monkeypatch.setattr(utils, "parse_research_event", MagicMock(side_effect=failure))
    with pytest.raises(RuntimeError) as exc:
        await utils.async_stream_sse_events(response).__anext__()
    assert exc.value is failure
    response.aclose.assert_awaited_once_with()


def test_sync_explicit_generator_close_releases_response():
    response = sync_response(EVENT_LINES + [""])
    stream = utils.stream_sse_events(response)
    assert next(stream).research_id == "research_123"
    response.close.assert_not_called()
    stream.close()
    stream.close()
    response.close.assert_called_once_with()


@pytest.mark.asyncio
async def test_async_explicit_generator_close_releases_response():
    response = async_response(EVENT_LINES + [""])
    stream = utils.async_stream_sse_events(response)
    assert (await stream.__anext__()).research_id == "research_123"
    response.aclose.assert_not_awaited()
    await stream.aclose()
    await stream.aclose()
    response.aclose.assert_awaited_once_with()


@pytest.mark.asyncio
@pytest.mark.parametrize("after_event", [False, True])
async def test_async_cancellation_awaits_response_cleanup(after_event):
    response = async_response([])
    waiting = asyncio.Event()
    blocked = asyncio.Event()

    async def iterate():
        if after_event:
            for line in EVENT_LINES + [""]:
                yield line
        waiting.set()
        await blocked.wait()

    response.aiter_lines.return_value = iterate()
    stream = utils.async_stream_sse_events(response)
    if after_event:
        assert (await stream.__anext__()).research_id == "research_123"
    task = asyncio.create_task(stream.__anext__())
    await asyncio.wait_for(waiting.wait(), timeout=5)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    response.aclose.assert_awaited_once_with()


def test_public_research_get_stream_is_closable():
    parent = MagicMock()
    response = sync_response(EVENT_LINES + [""])
    parent.request.return_value = response
    stream = ResearchClient(parent).get("research_123", stream=True)
    assert next(stream).research_id == "research_123"
    stream.close()
    response.close.assert_called_once_with()
    assert parent.request.call_args.kwargs["params"]["stream"] == "true"


@pytest.mark.asyncio
async def test_real_httpx_response_releases_stream_on_early_close():
    class Body(httpx.AsyncByteStream):
        def __init__(self):
            self.closed = 0

        async def __aiter__(self):
            yield ("\n".join(EVENT_LINES) + "\n\n").encode("utf-8")
            yield b": keepalive\n\n"

        async def aclose(self):
            self.closed += 1

    body = Body()
    transport = httpx.MockTransport(lambda request: httpx.Response(200, stream=body))
    async with httpx.AsyncClient(transport=transport) as client:
        response = await client.send(
            client.build_request("GET", "https://example.test"), stream=True
        )
        parent = MagicMock()
        parent.async_request = AsyncMock(return_value=response)
        stream = await AsyncResearchClient(parent).get("research_123", stream=True)
        assert (await stream.__anext__()).research_id == "research_123"
        assert not response.is_closed
        await stream.aclose()
        assert response.is_closed
        assert body.closed == 1
