"""Every search-style method builds its SearchResponse from the API payload the same way.

search, search_and_contents, get_contents, find_similar and find_similar_and_contents
each return a SearchResponse of Result objects, on both Exa and AsyncExa. This
pins every Result field and the response-level fields each endpoint keeps.
"""

from unittest.mock import AsyncMock, patch

import pytest

from exa_py import AsyncExa, Exa
from exa_py.api import (
    ApiWarning,
    CompanyEntity,
    ContentStatus,
    CostDollars,
    DeepSearchOutput,
    Result,
    SearchNotice,
)

API_KEY = "test-key"

RAW_RESULT = {
    "url": "https://example.com/a",
    "id": "https://example.com/a",
    "title": "Example A",
    "score": 0.42,
    "publishedDate": "2025-01-02T00:00:00.000Z",
    "author": "Ada",
    "image": "https://example.com/a.png",
    "favicon": "https://example.com/favicon.ico",
    "subpages": [{"id": "https://example.com/a/1", "url": "https://example.com/a/1"}],
    "extras": {"links": ["https://example.com/b"], "imageLinks": ["https://example.com/c.png"]},
    "crawlDate": "2025-01-03T00:00:00.000Z",
    "snapshotAt": "2025-01-04T00:00:00.000Z",
    "text": "Body text",
    "summary": "A summary",
    "highlights": ["a highlight"],
    "highlightScores": [0.9],
    "entities": [
        {"id": "company-1", "type": "company", "version": 1, "properties": {"name": "Acme"}}
    ],
}

RESPONSE = {
    "results": [RAW_RESULT],
    "resolvedSearchType": "neural",
    "autoDate": "2025-01-01",
    "context": "combined context",
    "output": {"content": "synthesized", "grounding": []},
    "costDollars": {"total": 0.005, "search": {"neural": 0.005}},
    "searchTime": 123.4,
    "warnings": [{"code": "IGNORED_FIELD", "path": "/foo", "message": "foo is ignored"}],
    "notices": [{"code": "RESTRICTIONS_RELAXED", "path": "/query", "message": "relaxed"}],
    "statuses": [{"id": "https://example.com/a", "status": "success", "source": "cached"}],
}

# Which response-level fields each endpoint reads from the payload.
SEARCH_FIELDS = {"context", "output", "warnings", "notices"}
ENDPOINTS = [
    ("search", "a query", SEARCH_FIELDS),
    ("search_and_contents", "a query", SEARCH_FIELDS),
    ("get_contents", ["https://example.com/a"], {"context", "statuses"}),
    ("find_similar", "https://example.com", set()),
    ("find_similar_and_contents", "https://example.com", {"context"}),
]

EXPECTED_OPTIONAL = {
    "context": "combined context",
    "output": DeepSearchOutput(content="synthesized", grounding=[]),
    "warnings": [ApiWarning(code="IGNORED_FIELD", path="/foo", message="foo is ignored")],
    "notices": [SearchNotice(code="RESTRICTIONS_RELAXED", path="/query", message="relaxed")],
    "statuses": [ContentStatus(id="https://example.com/a", status="success", source="cached")],
}


def assert_response(response, kept_fields):
    assert len(response.results) == 1
    result = response.results[0]
    assert isinstance(result, Result)
    assert result.url == "https://example.com/a"
    assert result.id == "https://example.com/a"
    assert result.title == "Example A"
    assert result.score == 0.42
    assert result.published_date == "2025-01-02T00:00:00.000Z"
    assert result.author == "Ada"
    assert result.image == "https://example.com/a.png"
    assert result.favicon == "https://example.com/favicon.ico"
    assert result.subpages == [{"id": "https://example.com/a/1", "url": "https://example.com/a/1"}]
    assert result.extras == {
        "links": ["https://example.com/b"],
        "image_links": ["https://example.com/c.png"],
    }
    assert result.crawl_date == "2025-01-03T00:00:00.000Z"
    assert result.snapshot_at == "2025-01-04T00:00:00.000Z"
    assert result.text == "Body text"
    assert result.summary == "A summary"
    assert result.highlights == ["a highlight"]
    assert result.highlight_scores == [0.9]
    assert len(result.entities) == 1
    assert isinstance(result.entities[0], CompanyEntity)
    assert result.entities[0].id == "company-1"
    assert result.entities[0].properties.name == "Acme"

    assert response.resolved_search_type == "neural"
    assert response.auto_date == "2025-01-01"
    assert response.cost_dollars == CostDollars(total=0.005, search={"neural": 0.005})
    assert response.search_time == 123.4
    for field, expected in EXPECTED_OPTIONAL.items():
        assert getattr(response, field) == (expected if field in kept_fields else None), field


@pytest.mark.parametrize(("method", "arg", "kept_fields"), ENDPOINTS)
def test_sync_response_parsing(method, arg, kept_fields):
    exa = Exa(API_KEY)
    with patch.object(exa, "request", return_value=RESPONSE):
        response = getattr(exa, method)(arg)

    assert_response(response, kept_fields)


@pytest.mark.asyncio
@pytest.mark.parametrize(("method", "arg", "kept_fields"), ENDPOINTS)
async def test_async_response_parsing(method, arg, kept_fields):
    exa = AsyncExa(API_KEY)
    with patch.object(exa, "async_request", new=AsyncMock(return_value=RESPONSE)):
        response = await getattr(exa, method)(arg)

    assert_response(response, kept_fields)


@pytest.mark.parametrize(("method", "arg", "kept_fields"), ENDPOINTS)
def test_missing_optional_fields_parse_as_none(method, arg, kept_fields):
    exa = Exa(API_KEY)
    with patch.object(exa, "request", return_value={"results": [{"url": "https://example.com/a"}]}):
        response = getattr(exa, method)(arg)

    assert response.results[0].url == "https://example.com/a"
    assert response.results[0].entities is None
    assert response.resolved_search_type is None
    assert response.auto_date is None
    assert response.cost_dollars is None
    assert response.search_time is None
    assert response.statuses == ([] if "statuses" in kept_fields else None)
