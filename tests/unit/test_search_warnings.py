"""Offline tests for the `warnings` array on /search responses and streams."""

from dataclasses import fields
from unittest.mock import AsyncMock, patch

import pytest

from exa_py import AsyncExa, Exa
from exa_py import api as exa_api
from exa_py.api import SearchStreamChunk, SearchWarning, StreamChunk

API_KEY = "test-key"

IGNORED_START = {
    "code": "IGNORED_FIELD",
    "path": "/startCrawlDate",
    "message": "startCrawlDate is no longer supported and is ignored. Remove it from the request.",
}
IGNORED_END = {
    "code": "IGNORED_FIELD",
    "path": "/endCrawlDate",
    "message": "endCrawlDate is no longer supported and is ignored. Remove it from the request.",
}

SEARCH_RESPONSE = {
    "requestId": "req-1",
    "results": [{"url": "http://example.com", "id": "1", "title": "Example"}],
    "searchTime": 12.5,
    "warnings": [IGNORED_START, IGNORED_END],
}

# The SSE payloads /search streams: text deltas, then one `results` event that
# carries `warnings`, then `done` and [DONE].
SEARCH_STREAM_LINES = [
    'data: {"requestId":"req-1","type":"text-delta","delta":"Hello",'
    '"choices":[{"index":0,"delta":{"role":"assistant","content":"Hello"},"finish_reason":null}]}',
    "",
    'data: {"requestId":"req-1","type":"results",'
    '"results":[{"url":"http://example.com","id":"1","title":"Example"}],'
    '"warnings":[{"code":"IGNORED_FIELD","path":"/startCrawlDate",'
    '"message":"startCrawlDate is no longer supported and is ignored. Remove it from the request."}]}',
    "",
    'data: {"requestId":"req-1","type":"done","output":null,"searchTime":12.5,"costDollars":{"total":0.007},'
    '"choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}',
    "",
    "data: [DONE]",
]

EXPECTED_STREAM_WARNING = SearchWarning(
    code="IGNORED_FIELD",
    path="/startCrawlDate",
    message="startCrawlDate is no longer supported and is ignored. Remove it from the request.",
)


class _FakeStreamResponse:
    def __init__(self, lines: list[str]):
        self._lines = lines
        self.status_code = 200
        self.text = ""

    def iter_lines(self):
        for line in self._lines:
            yield line.encode("utf-8")

    def close(self):
        return None


class _FakeAsyncStreamResponse:
    def __init__(self, lines: list[str]):
        self._lines = lines
        self.status_code = 200
        self.text = ""

    async def aiter_lines(self):
        for line in self._lines:
            yield line

    async def aclose(self):
        return None


def test_parse_search_warnings_reads_each_item():
    assert exa_api.parse_search_warnings([IGNORED_START, IGNORED_END]) == [
        SearchWarning(**IGNORED_START),
        SearchWarning(**IGNORED_END),
    ]


def test_parse_search_warnings_is_none_without_an_array():
    assert exa_api.parse_search_warnings(None) is None
    assert exa_api.parse_search_warnings({"code": "IGNORED_FIELD"}) is None


def test_parse_search_warnings_skips_malformed_items():
    raw = [
        IGNORED_START,
        "IGNORED_FIELD",
        {"code": "IGNORED_FIELD", "path": "/endCrawlDate"},
        {"code": 1, "path": "/endCrawlDate", "message": "m"},
    ]

    assert exa_api.parse_search_warnings(raw) == [SearchWarning(**IGNORED_START)]


def test_parse_search_warnings_keeps_unknown_codes():
    unknown = {"code": "SOME_FUTURE_CODE", "path": "/x", "message": "m"}

    assert exa_api.parse_search_warnings([unknown]) == [SearchWarning(**unknown)]


def test_search_warning_has_no_details_field():
    assert [field.name for field in fields(SearchWarning)] == [
        "code",
        "path",
        "message",
    ]


def test_search_returns_warnings_offline():
    exa = Exa(API_KEY)

    with patch.object(exa, "request", return_value=SEARCH_RESPONSE):
        response = exa.search("rust release notes", start_crawl_date="2026-01-01")

    assert response.warnings == [
        SearchWarning(**IGNORED_START),
        SearchWarning(**IGNORED_END),
    ]


def test_search_without_warnings_offline():
    exa = Exa(API_KEY)
    payload = {
        key: value for key, value in SEARCH_RESPONSE.items() if key != "warnings"
    }

    with patch.object(exa, "request", return_value=payload):
        response = exa.search("rust release notes")

    assert response.warnings is None


def test_search_and_contents_returns_warnings_offline():
    exa = Exa(API_KEY)

    with patch.object(exa, "request", return_value=SEARCH_RESPONSE):
        with pytest.warns(DeprecationWarning):
            response = exa.search_and_contents("rust release notes")

    assert response.warnings == [
        SearchWarning(**IGNORED_START),
        SearchWarning(**IGNORED_END),
    ]


def test_contents_and_find_similar_leave_warnings_unset_offline():
    exa = Exa(API_KEY)

    with patch.object(exa, "request", return_value=SEARCH_RESPONSE):
        contents = exa.get_contents(["http://example.com"])
        with pytest.warns(DeprecationWarning):
            similar = exa.find_similar("http://example.com")

    assert contents.warnings is None
    assert similar.warnings is None


@pytest.mark.asyncio
async def test_async_search_returns_warnings_offline():
    ax = AsyncExa(API_KEY)

    with patch.object(ax, "async_request", new=AsyncMock(return_value=SEARCH_RESPONSE)):
        response = await ax.search("rust release notes")

    assert response.warnings == [
        SearchWarning(**IGNORED_START),
        SearchWarning(**IGNORED_END),
    ]


@pytest.mark.asyncio
async def test_async_search_and_contents_returns_warnings_offline():
    ax = AsyncExa(API_KEY)

    with patch.object(ax, "async_request", new=AsyncMock(return_value=SEARCH_RESPONSE)):
        with pytest.warns(DeprecationWarning):
            response = await ax.search_and_contents("rust release notes")

    assert response.warnings == [
        SearchWarning(**IGNORED_START),
        SearchWarning(**IGNORED_END),
    ]


def test_stream_search_yields_warnings_chunk_offline():
    exa = Exa(API_KEY)

    with patch.object(
        exa, "request", return_value=_FakeStreamResponse(SEARCH_STREAM_LINES)
    ):
        stream = exa.stream_search("rust release notes")
        chunks = list(stream)

    assert chunks == [
        SearchStreamChunk(content="Hello"),
        SearchStreamChunk(warnings=[EXPECTED_STREAM_WARNING]),
    ]
    assert stream.cost_dollars == exa_api.CostDollars(total=0.007)


def test_stream_search_without_warnings_yields_text_only_offline():
    exa = Exa(API_KEY)
    lines = [
        'data: {"type":"text-delta","delta":"Hi","choices":[{"index":0,"delta":{"content":"Hi"},"finish_reason":null}]}',
        'data: {"type":"results","results":[]}',
        "data: [DONE]",
    ]

    with patch.object(exa, "request", return_value=_FakeStreamResponse(lines)):
        chunks = list(exa.stream_search("rust release notes"))

    assert chunks == [SearchStreamChunk(content="Hi")]


@pytest.mark.asyncio
async def test_async_stream_search_yields_warnings_chunk_offline():
    ax = AsyncExa(API_KEY)

    with patch.object(
        ax,
        "async_request",
        new=AsyncMock(return_value=_FakeAsyncStreamResponse(SEARCH_STREAM_LINES)),
    ):
        stream = await ax.stream_search("rust release notes")
        chunks = [chunk async for chunk in stream]

    assert chunks == [
        SearchStreamChunk(content="Hello"),
        SearchStreamChunk(warnings=[EXPECTED_STREAM_WARNING]),
    ]


def test_answer_stream_chunks_carry_no_warnings():
    stream = exa_api.StreamAnswerResponse(_FakeStreamResponse(SEARCH_STREAM_LINES))

    chunks = list(stream)

    assert chunks == [StreamChunk(content="Hello")]
    assert type(chunks[0]) is StreamChunk
