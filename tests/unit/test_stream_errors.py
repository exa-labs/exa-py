"""A stream the API ends with an error event raises, after the chunks that came before it."""

import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import requests

from exa_py import AsyncExa, Exa
from exa_py.api import SearchStreamChunk, StreamChunk

TEXT_DELTA = '{"index":0,"delta":{"content":"partial"},"finish_reason":null}'
DONE = "data: [DONE]"

# Each case is a failed stream as the API sends it: some text, the error event, then [DONE].
CASES = [
    pytest.param(
        "stream_answer",
        [
            'data: {"choices":[' + TEXT_DELTA + "]}",
            'data: {"tag":"ERROR","payload":{"error":{"code":500,"message":"boom"},"requestId":"req-1"}}',
            DONE,
        ],
        StreamChunk(content="partial"),
        "Stream failed: boom (code: 500, request ID: req-1)",
        id="answer",
    ),
    pytest.param(
        "stream_search",
        [
            'data: {"requestId":"req-2","type":"text-delta","delta":"partial","choices":[' + TEXT_DELTA + "]}",
            'data: {"requestId":"req-2","type":"error","error":{"message":"Not offered here.","tag":"REGION"}}',
            DONE,
        ],
        SearchStreamChunk(content="partial"),
        "Stream failed: Not offered here. (tag: REGION, request ID: req-2)",
        id="search-with-tag",
    ),
    pytest.param(
        "stream_search",
        [
            'data: {"requestId":"req-3","type":"text-delta","delta":"partial","choices":[' + TEXT_DELTA + "]}",
            'data: {"requestId":"req-3","type":"error","error":{"message":"Search stream failed."}}',
            DONE,
        ],
        SearchStreamChunk(content="partial"),
        "Stream failed: Search stream failed. (request ID: req-3)",
        id="search-without-tag",
    ),
]


@pytest.mark.parametrize("method, lines, chunk, message", CASES)
def test_sync_stream_raises_the_api_error_after_the_text_before_it(method, lines, chunk, message):
    response = requests.Response()
    response.status_code = 200
    response.headers["content-type"] = "text/event-stream"
    response.raw = io.BytesIO("".join(line + "\n\n" for line in lines).encode())
    exa = Exa("test-key")
    with patch.object(exa, "request", return_value=response):
        stream = getattr(exa, method)("q")

    received = []
    with pytest.raises(ValueError) as raised:
        for item in stream:
            received.append(item)

    assert received == [chunk]
    assert str(raised.value) == message
    assert response.raw.closed, "the failed stream's connection was left open"


@pytest.mark.asyncio
@pytest.mark.parametrize("method, lines, chunk, message", CASES)
async def test_async_stream_raises_the_api_error_after_the_text_before_it(method, lines, chunk, message):
    async def aiter_lines():
        for line in lines:
            yield line

    raw = MagicMock(
        status_code=200,
        headers={"content-type": "text/event-stream"},
        aiter_lines=aiter_lines,
        aclose=AsyncMock(),
    )
    ax = AsyncExa("test-key")
    with patch.object(ax, "async_request", new=AsyncMock(return_value=raw)):
        stream = await getattr(ax, method)("q")

    received = []
    with pytest.raises(ValueError) as raised:
        async for item in stream:
            received.append(item)

    assert received == [chunk]
    assert str(raised.value) == message
