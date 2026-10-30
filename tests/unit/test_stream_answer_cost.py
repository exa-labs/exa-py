"""The cost an /answer stream reports in its final event is kept on the stream."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from exa_py import AsyncExa, Exa
from exa_py.api import CostDollars, StreamChunk

ANSWER_STREAM_LINES = [
    'data: {"choices":[{"index":0,"delta":{"content":"Paris"},"finish_reason":null}]}',
    'data: {"costDollars":{"total":0.005},"requestId":"req-1"}',
    "data: [DONE]",
]


def test_stream_answer_keeps_the_cost():
    raw = MagicMock(status_code=200)
    raw.iter_lines.return_value = [line.encode() for line in ANSWER_STREAM_LINES]
    exa = Exa("test-key")
    with patch.object(exa, "request", return_value=raw):
        stream = exa.stream_answer("q")

    assert list(stream) == [StreamChunk(content="Paris")]
    assert stream.cost_dollars == CostDollars(total=0.005)


@pytest.mark.asyncio
async def test_async_stream_answer_keeps_the_cost():
    async def lines():
        for line in ANSWER_STREAM_LINES:
            yield line

    raw = MagicMock(status_code=200, aiter_lines=lines, aclose=AsyncMock())
    ax = AsyncExa("test-key")
    with patch.object(ax, "async_request", new=AsyncMock(return_value=raw)):
        stream = await ax.stream_answer("q")

    assert [chunk async for chunk in stream] == [StreamChunk(content="Paris")]
    assert stream.cost_dollars == CostDollars(total=0.005)
