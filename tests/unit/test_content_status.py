"""get_contents keeps every field of each URL's status, including the error detail."""

from unittest.mock import AsyncMock, patch

import pytest

from exa_py import AsyncExa, Exa
from exa_py.api import ContentStatus, ContentStatusError

API_KEY = "test-key"

CONTENTS_RESPONSE = {
    "results": [],
    "statuses": [
        {"id": "https://ok.example", "status": "success", "source": "crawled"},
        {
            "id": "https://gone.example",
            "status": "error",
            "error": {"tag": "CRAWL_NOT_FOUND", "httpStatusCode": 404},
        },
        {
            "id": "https://down.example",
            "status": "error",
            "error": {"tag": "CRAWL_TIMEOUT", "httpStatusCode": None},
        },
        {"id": "https://cached.example", "status": "success", "source": "cached", "error": None},
    ],
}

EXPECTED_STATUSES = [
    ContentStatus(id="https://ok.example", status="success", source="crawled"),
    ContentStatus(
        id="https://gone.example",
        status="error",
        error=ContentStatusError(tag="CRAWL_NOT_FOUND", http_status_code=404),
    ),
    ContentStatus(
        id="https://down.example",
        status="error",
        error=ContentStatusError(tag="CRAWL_TIMEOUT", http_status_code=None),
    ),
    ContentStatus(id="https://cached.example", status="success", source="cached"),
]

URLS = [status["id"] for status in CONTENTS_RESPONSE["statuses"]]


def test_get_contents_keeps_status_error_detail():
    exa = Exa(API_KEY)
    with patch.object(exa, "request", return_value=CONTENTS_RESPONSE):
        response = exa.get_contents(URLS)

    assert response.statuses == EXPECTED_STATUSES


@pytest.mark.asyncio
async def test_async_get_contents_keeps_status_error_detail():
    exa = AsyncExa(API_KEY)
    with patch.object(
        exa, "async_request", new=AsyncMock(return_value=CONTENTS_RESPONSE)
    ):
        response = await exa.get_contents(URLS)

    assert response.statuses == EXPECTED_STATUSES


def test_content_status_source_and_error_default_to_none():
    status = ContentStatus(id="https://example.com", status="success")

    assert status.source is None
    assert status.error is None
