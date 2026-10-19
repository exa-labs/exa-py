"""Transport timeouts stay out of API bodies and reach both HTTP stacks."""

import asyncio
import json
import threading
import warnings
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
import requests

from exa_py import AsyncExa, Exa
from exa_py.websets.imports.client import AsyncImportsClient, ImportsClient


def _response() -> requests.Response:
    response = requests.Response()
    response.status_code = 200
    response._content = b'{"results":[],"citations":[],"answer":"ok"}'
    return response


@pytest.mark.parametrize("method", ["GET", "POST", "PATCH", "DELETE"])
def test_sync_default_and_per_call_timeout(method):
    exa = Exa("test-key", timeout=12)
    with patch(f"exa_py.api.requests.{method.lower()}", return_value=_response()) as send:
        exa.request("/search", {"query": "test"}, method=method)
        assert send.call_args.kwargs["timeout"] == 12
        exa.request("/search", {"query": "test"}, method=method, timeout=2)
        assert send.call_args.kwargs["timeout"] == 2


@pytest.mark.parametrize("method", ["GET", "POST"])
def test_sync_stream_timeout_is_passed_to_socket(method):
    exa = Exa("test-key", timeout=10)
    with patch(f"exa_py.api.requests.{method.lower()}", return_value=_response()) as send:
        exa.request("/search", {"stream": True}, method=method, timeout=3)
        assert send.call_args.kwargs["stream"] is True
        assert send.call_args.kwargs["timeout"] == 3


def test_sync_high_level_timeout_does_not_enter_api_body():
    exa = Exa("test-key", timeout=20)
    with patch("exa_py.api.requests.post", return_value=_response()) as send:
        exa.search("test", timeout=2, extra_body={"numResults": 3})
        assert send.call_args.kwargs["timeout"] == 2
        search_body = json.loads(send.call_args.kwargs["data"])
        assert search_body["numResults"] == 3
        assert "timeout" not in search_body
        assert "extraBody" not in search_body
        stream = exa.stream_search("test", timeout=3, extra_body={"numResults": 2})
        assert send.call_args.kwargs["timeout"] == 3
        assert json.loads(send.call_args.kwargs["data"])["numResults"] == 2
        stream.close()
        exa.get_contents("https://example.com", timeout=4)
        assert send.call_args.kwargs["timeout"] == 4
        assert "timeout" not in send.call_args.kwargs["data"]
        exa.answer("test", timeout=5)
        assert send.call_args.kwargs["timeout"] == 5
        assert "timeout" not in send.call_args.kwargs["data"]


@pytest.mark.parametrize(
    "invalid",
    [0, -1, float("nan"), float("inf"), True, "3", threading.TIMEOUT_MAX * 2, 1e300],
)
def test_invalid_timeout_is_rejected_consistently(invalid):
    with pytest.raises(ValueError, match="timeout must be"):
        Exa("test-key", timeout=invalid)
    with pytest.raises(ValueError, match="timeout must be"):
        AsyncExa("test-key", timeout=invalid)
    exa = Exa("test-key")
    with pytest.raises(ValueError, match="timeout must be"):
        exa.request("/search", timeout=invalid)


def test_the_longest_timeout_python_supports_is_accepted():
    exa = Exa("test-key", timeout=threading.TIMEOUT_MAX)
    assert AsyncExa("test-key", timeout=threading.TIMEOUT_MAX).timeout == threading.TIMEOUT_MAX
    with patch("exa_py.api.requests.post", return_value=_response()) as send:
        exa.request("/search", {"query": "test"}, timeout=threading.TIMEOUT_MAX)
    assert send.call_args.kwargs["timeout"] == threading.TIMEOUT_MAX


def test_constructor_none_disables_sync_timeout():
    exa = Exa("test-key", timeout=None)
    with patch("exa_py.api.requests.get", return_value=_response()) as send:
        exa.request("/search", method="GET")
        assert send.call_args.kwargs["timeout"] is None


@pytest.mark.asyncio
async def test_async_timeout_reaches_all_methods_and_streams():
    seen: list[httpx.Request] = []
    # The timeouts each request was sent with: a stream's read timeout is
    # lifted once its response starts.
    sent_with: list[dict] = []

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        sent_with.append(dict(request.extensions["timeout"]))
        return httpx.Response(200, json={"results": [], "citations": [], "answer": "ok"})

    exa = AsyncExa("test-key", timeout=16)
    exa._client = httpx.AsyncClient(transport=httpx.MockTransport(handle), timeout=exa.timeout)
    try:
        for method in ("GET", "POST", "PATCH", "DELETE"):
            await exa.async_request("/search", {"query": "test"}, method=method, timeout=2)
            assert sent_with[-1]["read"] == 2
            assert seen[-1].extensions["timeout"]["read"] == 2
        for method in ("GET", "POST"):
            response = await exa.async_request("/search", {"stream": True}, method=method, timeout=3)
            assert sent_with[-1] == {"connect": 3, "read": 3, "write": 3, "pool": 3}
            assert seen[-1].extensions["timeout"] == {"connect": 3, "read": None, "write": 3, "pool": 3}
            await response.aclose()
        await exa.search("test", timeout=4, extra_body={"numResults": 3})
        assert sent_with[-1]["read"] == 4
        search_body = json.loads(seen[-1].content)
        assert search_body["numResults"] == 3
        assert "timeout" not in search_body
        assert "extraBody" not in search_body
        stream = await exa.stream_search("test", timeout=4, extra_body={"numResults": 2})
        assert sent_with[-1]["read"] == 4
        assert json.loads(seen[-1].content)["numResults"] == 2
        await stream.aclose()
        await exa.get_contents("https://example.com", timeout=5)
        assert sent_with[-1]["read"] == 5
        assert "timeout" not in seen[-1].content.decode()
        await exa.answer("test", timeout=6)
        assert sent_with[-1]["read"] == 6
        assert "timeout" not in seen[-1].content.decode()
        await exa.async_request("/search", method="GET")
        assert sent_with[-1]["read"] == 16
    finally:
        await exa._client.aclose()


@pytest.mark.asyncio
async def test_async_client_closes_its_connections_on_aclose_and_on_leaving_async_with():
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"results": []}))
    async with AsyncExa("test-key") as exa:
        exa._client = first = httpx.AsyncClient(transport=transport)
        await exa.search("test")
    assert first.is_closed
    assert exa._client is None

    # A request made after closing opens new connections; closing twice is safe.
    second = exa.client
    assert second is not first and not second.is_closed
    await exa.aclose()
    await exa.aclose()
    assert second.is_closed


@pytest.mark.asyncio
async def test_async_none_disables_timeout():
    exa = AsyncExa("test-key", timeout=None)
    assert exa.client.timeout.read is None
    await exa.client.aclose()


@pytest.mark.asyncio
async def test_cancelled_stream_iteration_closes_the_async_response():
    class GatedStream(httpx.AsyncByteStream):
        def __init__(self):
            self.waiting = asyncio.Event()
            self.closed = False

        async def __aiter__(self):
            yield b'data: {"choices":[{"delta":{"content":"first"}}]}\n'
            self.waiting.set()
            await asyncio.Event().wait()

        async def aclose(self):
            self.closed = True

    body = GatedStream()
    exa = AsyncExa("test-key", timeout=1)
    exa._client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, stream=body)),
        timeout=exa.timeout,
    )
    try:
        stream = await exa.stream_answer("test")
        iterator = stream.__aiter__()
        assert (await iterator.__anext__()).content == "first"
        next_chunk = asyncio.create_task(iterator.__anext__())
        await body.waiting.wait()
        next_chunk.cancel()
        with pytest.raises(asyncio.CancelledError):
            await next_chunk
        assert body.closed
        await stream.aclose()  # Explicit early-close is also safe after cancellation.
        with pytest.raises(RuntimeError, match="await stream.aclose"):
            stream.close()
    finally:
        await exa._client.aclose()


_IMPORT = {
    "id": "imp_1", "object": "import", "status": "pending", "format": "csv",
    "title": "test", "count": 1, "metadata": {},
    "createdAt": "2026-01-01T00:00:00Z", "updatedAt": "2026-01-01T00:00:00Z",
    "uploadUrl": "https://example.com/upload", "uploadValidUntil": "2026-01-01T01:00:00Z",
}


def test_sync_import_upload_inherits_client_timeout():
    exa = Exa("test-key", timeout=8)
    client = ImportsClient(exa)
    with patch.object(client, "request", return_value=_IMPORT), patch.object(client, "get", return_value=object()), patch("exa_py.websets.imports.client.requests.put", return_value=Mock()) as upload:
        client.create({}, csv_data="url\nhttps://example.com")
        assert upload.call_args.kwargs["timeout"] == 8


@pytest.mark.asyncio
async def test_async_import_upload_inherits_timeout_and_uses_separate_client():
    exa = AsyncExa("test-key", timeout=None)
    client = AsyncImportsClient(exa)
    async_transport = AsyncMock()
    async_transport.put.return_value.raise_for_status = Mock()
    async_transport.__aenter__.return_value = async_transport
    with patch.object(client, "request", new_callable=AsyncMock, return_value=_IMPORT), patch.object(client, "get", new_callable=AsyncMock, return_value=object()), patch("exa_py.websets.imports.client.httpx.AsyncClient", return_value=async_transport) as constructor:
        await client.create({}, csv_data="url\nhttps://example.com")
        constructor.assert_called_once_with(timeout=None)
        assert "x-api-key" not in async_transport.put.call_args.kwargs.get("headers", {})


@pytest.mark.asyncio
async def test_async_import_upload_sends_the_csv_without_a_deprecation_warning():
    uploads = []

    def handle(request: httpx.Request) -> httpx.Response:
        uploads.append((request.method, request.headers["Content-Type"], request.content))
        return httpx.Response(200)

    real_client = httpx.AsyncClient
    client = AsyncImportsClient(AsyncExa("test-key"))
    with patch.object(client, "request", new_callable=AsyncMock, return_value=_IMPORT), patch.object(
        client, "get", new_callable=AsyncMock, return_value=object()
    ), patch(
        "exa_py.websets.imports.client.httpx.AsyncClient",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handle), **kwargs),
    ), warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        await client.create({}, csv_data="url\nhttps://example.com")
    assert uploads == [("PUT", "text/csv", b"url\nhttps://example.com")]
