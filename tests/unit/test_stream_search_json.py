"""`stream_search` when the API answers with the whole search response as JSON.

The API answers a search without `output_schema` with its normal JSON response
instead of an event stream. Both clients run against a local HTTP server, so
the real request, error and timeout paths are covered.
"""

import json
import threading
import warnings
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional

import httpx
import pytest
import requests

from exa_py import AsyncExa, Exa, ExaTimeoutError, ExaWarning
from exa_py.api import AnswerResult, SearchStreamChunk, SearchWarning, _is_json_content_type

API_KEY = "test-key"
JSON_CONTENT_TYPE = "application/json; charset=utf-8"
CLIENTS = ["sync", "async"]

IGNORED_START = {
    "code": "IGNORED_FIELD",
    "path": "/startCrawlDate",
    "message": "startCrawlDate is no longer supported and is ignored. Remove it from the request.",
}

# A /search response as the API sends it when it does not stream.
SEARCH_RESPONSE: Dict[str, Any] = {
    "requestId": "req-json-1",
    "resolvedSearchType": "neural",
    "results": [
        {
            "id": "https://example.com/a",
            "url": "https://example.com/a",
            "title": "Alpha",
            "publishedDate": "2026-01-02T00:00:00.000Z",
            "author": "Ada",
            "text": "Alpha text",
            "score": 0.9,
            "highlights": ["Alpha highlight"],
        },
        {"id": "https://example.com/b", "url": "https://example.com/b", "title": None},
    ],
    "searchTime": 12.5,
    "costDollars": {"total": 0.007},
}

# The citations stream_search makes of SEARCH_RESPONSE["results"].
RESULT_CITATIONS = [
    AnswerResult(
        id="https://example.com/a",
        url="https://example.com/a",
        title="Alpha",
        published_date="2026-01-02T00:00:00.000Z",
        author="Ada",
        text="Alpha text",
    ),
    AnswerResult(id="https://example.com/b", url="https://example.com/b"),
]


class _Server:
    """A local API server that answers every request with the reply a test sets.

    `requests` collects the decoded body of each request it receives. A reply
    can hold back its headers for `headers_delay` seconds, or pause for
    `body_pause` seconds after the first 20 bytes of its body.
    """

    def __init__(self) -> None:
        self.requests: List[Any] = []
        self.status = 200
        self.content_type = JSON_CONTENT_TYPE
        self.body = b""
        self.headers_delay = 0.0
        self.body_pause = 0.0
        self._release = threading.Event()
        server = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def do_POST(self):
                raw = self.rfile.read(int(self.headers.get("Content-Length", 0)))
                server.requests.append(json.loads(raw) if raw else None)
                if server.headers_delay and server._release.wait(server.headers_delay):
                    return
                self.send_response(server.status)
                self.send_header("Content-Type", server.content_type)
                self.send_header("Content-Length", str(len(server.body)))
                self.end_headers()
                head, rest = server.body[:20], server.body[20:]
                self.wfile.write(head)
                self.wfile.flush()
                if server.body_pause and server._release.wait(server.body_pause):
                    return
                self.wfile.write(rest)
                self.wfile.flush()

            def log_message(self, *args):
                pass

        self._http = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._http.daemon_threads = True
        self.url = f"http://127.0.0.1:{self._http.server_address[1]}"
        threading.Thread(target=self._http.serve_forever, daemon=True).start()

    def reply(self, body: Any, status: int = 200, content_type: str = JSON_CONTENT_TYPE) -> None:
        """Answer with `body`, serialized as JSON unless it is already a string."""
        self.status = status
        self.content_type = content_type
        self.body = (body if isinstance(body, str) else json.dumps(body)).encode("utf-8")

    def close(self) -> None:
        self._release.set()
        self._http.shutdown()
        self._http.server_close()


@pytest.fixture
def server():
    api = _Server()
    try:
        yield api
    finally:
        api.close()


async def call(client: str, base_url: str, method: str, timeout: float = 5.0) -> Any:
    """Call `method` ("search" or "stream_search") with the sync or async client.

    A stream is read whole and returned as its list of chunks.
    """
    if client == "sync":
        exa = Exa(API_KEY, base_url=base_url, timeout=timeout)
        result = getattr(exa, method)("q", num_results=2)
        return list(result) if method == "stream_search" else result
    async with AsyncExa(API_KEY, api_base=base_url, timeout=timeout) as async_exa:
        result = await getattr(async_exa, method)("q", num_results=2)
        return [chunk async for chunk in result] if method == "stream_search" else result


async def call_error(client: str, base_url: str, method: str, timeout: float = 5.0) -> BaseException:
    """The exception `call` raises."""
    with pytest.raises(Exception) as raised:
        await call(client, base_url, method, timeout)
    return raised.value


def exa_warnings(caught: List[warnings.WarningMessage]) -> List[warnings.WarningMessage]:
    return [w for w in caught if issubclass(w.category, ExaWarning)]


@pytest.mark.asyncio
@pytest.mark.parametrize("client", CLIENTS)
async def test_yields_the_results_as_citations_then_the_warnings(server, client):
    server.reply({**SEARCH_RESPONSE, "warnings": [IGNORED_START]})

    chunks = await call(client, server.url, "stream_search")

    assert chunks == [
        SearchStreamChunk(citations=RESULT_CITATIONS),
        SearchStreamChunk(warnings=[SearchWarning(**IGNORED_START)]),
    ]
    assert server.requests[0]["stream"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize("client", CLIENTS)
@pytest.mark.parametrize("warnings_field", [{}, {"warnings": []}], ids=["absent", "empty"])
async def test_yields_only_the_results_without_warnings(server, client, warnings_field):
    server.reply({**SEARCH_RESPONSE, **warnings_field})

    chunks = await call(client, server.url, "stream_search")

    assert chunks == [SearchStreamChunk(citations=RESULT_CITATIONS)]


@pytest.mark.asyncio
@pytest.mark.parametrize("client", CLIENTS)
async def test_yields_only_the_warnings_without_results(server, client):
    server.reply({"requestId": "req-1", "results": [], "warnings": [IGNORED_START]})

    chunks = await call(client, server.url, "stream_search")

    assert chunks == [SearchStreamChunk(warnings=[SearchWarning(**IGNORED_START)])]


@pytest.mark.asyncio
@pytest.mark.parametrize("client", CLIENTS)
async def test_yields_nothing_without_results_or_warnings(server, client):
    server.reply({"requestId": "req-1", "results": []})

    assert await call(client, server.url, "stream_search") == []


@pytest.mark.asyncio
@pytest.mark.parametrize("client", CLIENTS)
async def test_reports_the_warnings_once_at_the_calling_line(server, client):
    server.reply({**SEARCH_RESPONSE, "warnings": [IGNORED_START]})

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        chunks = await call(client, server.url, "stream_search")

    issued = exa_warnings(caught)
    assert [str(w.message) for w in issued] == [
        "[exa] POST /search IGNORED_FIELD at /startCrawlDate: "
        "startCrawlDate is no longer supported and is ignored. Remove it from the request."
    ]
    assert issued[0].message.request_id == "req-json-1"
    assert issued[0].filename == __file__
    assert chunks[1].warnings == [issued[0].message.warning]


def test_reports_the_warnings_before_the_first_chunk(server):
    server.reply({**SEARCH_RESPONSE, "warnings": [IGNORED_START]})
    stream = Exa(API_KEY, base_url=server.url).stream_search("q")

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        first = next(iter(stream))

    assert first == SearchStreamChunk(citations=RESULT_CITATIONS)
    assert len(exa_warnings(caught)) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("client", CLIENTS)
@pytest.mark.parametrize(
    "body, message",
    [
        ("<html>Moved</html>", "Expected a JSON response but received a non-JSON body (status 200): <html>Moved</html>"),
        ("", "Expected a JSON response but received an empty body (status 200)."),
    ],
    ids=["html", "empty"],
)
async def test_a_json_response_whose_body_is_not_json_raises_as_search_does(server, client, body, message):
    server.reply(body)

    from_stream = await call_error(client, server.url, "stream_search")
    from_search = await call_error(client, server.url, "search")

    assert type(from_stream) is ValueError
    assert str(from_stream) == message == str(from_search)


@pytest.mark.asyncio
@pytest.mark.parametrize("client", CLIENTS)
@pytest.mark.parametrize(
    "status, body",
    [
        (400, {"error": "Invalid request body", "requestId": "req_400"}),
        (429, {"error": {"type": "RATE_LIMITED", "message": "Slow down"}, "requestId": "req_429"}),
        (500, {"error": "Internal Server Error", "requestId": "req_500"}),
    ],
)
async def test_an_error_status_raises_as_search_does(server, client, status, body):
    server.reply(body, status=status)

    from_stream = await call_error(client, server.url, "stream_search")
    from_search = await call_error(client, server.url, "search")

    assert type(from_stream) is ValueError
    assert str(from_stream) == f"Request failed with status code {status}: {json.dumps(body)}"
    assert str(from_stream) == str(from_search)


@pytest.mark.asyncio
@pytest.mark.parametrize("client", CLIENTS)
async def test_a_response_that_never_starts_times_out(server, client):
    server.reply(SEARCH_RESPONSE)
    server.headers_delay = 5.0

    error = await call_error(client, server.url, "stream_search", timeout=0.2)

    assert isinstance(error, ExaTimeoutError)
    assert isinstance(error, requests.exceptions.ReadTimeout if client == "sync" else httpx.ReadTimeout)


@pytest.mark.asyncio
@pytest.mark.parametrize("client", CLIENTS)
async def test_a_slow_json_body_is_not_cut_once_the_response_starts(server, client):
    server.reply(SEARCH_RESPONSE)
    server.body_pause = 0.6

    chunks = await call(client, server.url, "stream_search", timeout=0.3)

    assert chunks == [SearchStreamChunk(citations=RESULT_CITATIONS)]


@pytest.mark.asyncio
@pytest.mark.parametrize("client", CLIENTS)
async def test_an_event_stream_is_still_parsed_as_one(server, client):
    events = [
        {"choices": [{"index": 0, "delta": {"content": "Hello"}}]},
        {"type": "results", "results": [], "warnings": [IGNORED_START]},
    ]
    server.reply(
        "".join(f"data: {json.dumps(event)}\n\n" for event in events) + "data: [DONE]\n\n",
        content_type="text/event-stream; charset=utf-8",
    )

    chunks = await call(client, server.url, "stream_search")

    assert chunks == [
        SearchStreamChunk(content="Hello"),
        SearchStreamChunk(warnings=[SearchWarning(**IGNORED_START)]),
    ]


@pytest.mark.parametrize(
    "content_type, expected",
    [
        ("application/json", True),
        ("application/json; charset=utf-8", True),
        ("Application/JSON;charset=UTF-8", True),
        ("application/problem+json", True),
        ("text/event-stream", False),
        ("text/event-stream; charset=utf-8", False),
        ("text/html", False),
        ("", False),
        (None, False),
    ],
)
def test_is_json_content_type(content_type: Optional[str], expected: bool):
    assert _is_json_content_type(content_type) is expected
