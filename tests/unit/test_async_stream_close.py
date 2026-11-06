"""Public async stream lifecycle regressions against mocked HTTP transport.

The SDK already implements async closing via `aclose()`. These tests cover
unread, partially read, and exhausted answer/search streams without API calls.
"""

from typing import AsyncIterator
from unittest.mock import patch

import httpx
import pytest

from exa_py import AsyncExa


class _TrackedAsyncStream(httpx.AsyncByteStream):
    def __init__(self) -> None:
        self.closed = False
        self.close_calls = 0
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
        self.close_calls += 1


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["stream_answer", "stream_search"])
@pytest.mark.parametrize("read_state", ["unread", "early_exit", "finished"])
async def test_async_stream_lifecycle_aclose(method: str, read_state: str) -> None:
    """Either stream API can release the response before or after consumption."""
    body = _TrackedAsyncStream()
    response = httpx.Response(200, stream=body)

    def respond(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        return response

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        with patch("exa_py.api.httpx.AsyncClient", return_value=client):
            exa = AsyncExa("test-key")
            stream = await getattr(exa, method)("research query")

        iterator = stream.__aiter__() if read_state != "unread" else None
        try:
            assert not body.closed
            chunks = []
            if read_state == "early_exit":
                assert iterator is not None
                chunks.append((await iterator.__anext__()).content)
            elif read_state == "finished":
                assert iterator is not None
                chunks = [chunk.content async for chunk in iterator]

            assert chunks == {
                "unread": [],
                "early_exit": ["first"],
                "finished": ["first", "second"],
            }[read_state]
            assert body.chunks_read == len(chunks)
            assert body.closed is (read_state == "finished")

            await stream.aclose()
            assert response.is_closed
            assert body.closed

            # Response-level closing is idempotent for every lifecycle state.
            await stream.aclose()
            assert body.close_calls == 1
        finally:
            if iterator is not None:
                await iterator.aclose()
            await stream.aclose()
