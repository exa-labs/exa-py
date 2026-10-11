from typing import AsyncIterator
from unittest.mock import patch

import httpx
import pytest

from exa_py import AsyncExa


class _TrackedAsyncStream(httpx.AsyncByteStream):
    def __init__(self) -> None:
        self.closed = False
        self.chunks_read = 0

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for content in ("first", "second"):
            self.chunks_read += 1
            yield (
                'data: {"choices":[{"delta":{"content":"'
                + content
                + '"}}]}\n\n'
            ).encode()

    async def aclose(self) -> None:
        self.closed = True


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["stream_answer", "stream_search"])
@pytest.mark.parametrize("read_state", ["unread", "early_exit", "finished"])
async def test_async_stream_can_close(method: str, read_state: str) -> None:
    """A caller can release the HTTP response at any stage of iteration."""
    raw_stream = _TrackedAsyncStream()
    raw_response = httpx.Response(200, stream=raw_stream)

    def respond(request: httpx.Request) -> httpx.Response:
        return raw_response

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        with patch("exa_py.api.httpx.AsyncClient", return_value=client):
            exa = AsyncExa("test-key")
            stream = await getattr(exa, method)("research query")

        chunks = []
        if read_state != "unread":
            async for chunk in stream:
                chunks.append(chunk.content)
                if read_state == "early_exit":
                    break

        expected_chunks = {
            "unread": [],
            "early_exit": ["first"],
            "finished": ["first", "second"],
        }[read_state]
        assert chunks == expected_chunks
        assert raw_stream.chunks_read == len(expected_chunks)
        assert raw_stream.closed is (read_state == "finished")
        try:
            await stream.close()
            assert raw_stream.closed
            await stream.close()
        finally:
            await raw_response.aclose()
