"""Offline tests for the Python warnings the SDK issues about a request.

`ExaWarning` for each warning the API returns in a response, issued from
`request` / `async_request` and the search stream, and `DeprecationWarning`
for deprecated fields in the request body. Each is attributed to the caller's
own line. No real HTTP: the transport (`requests.post`, the async client) is
patched so the SDK's own `request` runs, or `request` itself for streams.
"""

import json
import logging
import pickle
import warnings
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import requests

from exa_py import ApiWarning, AsyncExa, Exa, ExaWarning
from exa_py.api import SearchWarning

API_KEY = "test-key"


def ignored(field: str) -> dict:
    return {
        "code": "IGNORED_FIELD",
        "path": f"/{field}",
        "message": f"{field} is no longer supported and is ignored. Remove it from the request.",
    }


def search_payload(*items: dict, request_id: str = "req-1") -> dict:
    payload = {
        "results": [{"url": "http://example.com", "id": "1", "title": "Example"}],
    }
    if request_id:
        payload["requestId"] = request_id
    if items:
        payload["warnings"] = list(items)
    return payload


def _http_response(payload, headers=None) -> requests.Response:
    response = requests.Response()
    response.status_code = 200
    response._content = json.dumps(payload).encode("utf-8")
    response.headers.update(headers or {})
    return response


class _FakeStreamResponse:
    def __init__(self, lines):
        self._lines = lines
        self.status_code = 200
        self.text = ""

    def iter_lines(self):
        for line in self._lines:
            yield line.encode("utf-8")

    def close(self):
        return None


def exa_warnings(caught):
    return [w for w in caught if issubclass(w.category, ExaWarning)]


def deprecation_messages(caught):
    return [str(w.message) for w in caught if issubclass(w.category, DeprecationWarning)]


def test_search_warning_is_the_generic_api_warning():
    assert SearchWarning is ApiWarning


def test_search_issues_an_exa_warning_per_item_at_the_calling_line():
    exa = Exa(API_KEY)

    with patch("exa_py.api.requests.post", return_value=_http_response(search_payload(ignored("a"), ignored("b")))):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            response = exa.search("rust release notes")

    issued = exa_warnings(caught)
    assert [str(w.message) for w in issued] == [
        "[exa] POST /search IGNORED_FIELD at /a: a is no longer supported and is ignored. Remove it from the request.",
        "[exa] POST /search IGNORED_FIELD at /b: b is no longer supported and is ignored. Remove it from the request.",
    ]
    assert [w.message.warning for w in issued] == response.warnings
    assert {(w.message.endpoint, w.message.method, w.message.request_id) for w in issued} == {
        ("/search", "POST", "req-1")
    }
    assert {w.filename for w in issued} == {__file__}


def test_request_id_falls_back_to_the_response_header():
    exa = Exa(API_KEY)
    response = _http_response(search_payload(ignored("a"), request_id=""), headers={"x-request-id": "hdr-1"})

    with patch("exa_py.api.requests.post", return_value=response):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            exa.search("rust release notes")

    assert [w.message.request_id for w in exa_warnings(caught)] == ["hdr-1"]


def test_default_filter_shows_each_warning_once_per_calling_line():
    exa = Exa(API_KEY)

    with patch("exa_py.api.requests.post", return_value=_http_response(search_payload(ignored("a")))):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("default")
            for _ in range(3):
                exa.search("rust release notes")

    assert len(exa_warnings(caught)) == 1


def test_ignoring_exa_warnings_keeps_them_on_the_response():
    exa = Exa(API_KEY)

    with patch("exa_py.api.requests.post", return_value=_http_response(search_payload(ignored("a")))):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            warnings.filterwarnings("ignore", category=ExaWarning)
            response = exa.search("rust release notes")

    assert exa_warnings(caught) == []
    assert response.warnings == [ApiWarning(**ignored("a"))]


def test_capture_warnings_routes_exa_warnings_to_logging(caplog):
    exa = Exa(API_KEY)

    with patch("exa_py.api.requests.post", return_value=_http_response(search_payload(ignored("logged")))):
        with warnings.catch_warnings():
            warnings.simplefilter("always")
            logging.captureWarnings(True)
            try:
                with caplog.at_level(logging.WARNING, logger="py.warnings"):
                    exa.search("rust release notes")
            finally:
                logging.captureWarnings(False)

    assert any("[exa] POST /search IGNORED_FIELD at /logged" in r.getMessage() for r in caplog.records)


def test_no_exa_warning_without_warnings():
    exa = Exa(API_KEY)

    with patch("exa_py.api.requests.post", return_value=_http_response(search_payload())):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            exa.search("rust release notes")

    assert exa_warnings(caught) == []


def test_other_endpoints_warnings_fields_are_not_read():
    exa = Exa(API_KEY)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with patch("exa_py.api.requests.get", return_value=_http_response({"warnings": ["envelope truncated"]})):
            exa.request("/agent/v0/monitors/m1", method="GET")
        with patch("exa_py.api.requests.post", return_value=_http_response({"warnings": [ignored("a")]})):
            exa.request("/contents", {"urls": ["http://example.com"]})

    assert exa_warnings(caught) == []


def test_search_and_contents_attributes_past_its_deprecation_wrapper():
    exa = Exa(API_KEY)

    with patch("exa_py.api.requests.post", return_value=_http_response(search_payload(ignored("a")))):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            exa.search_and_contents("rust release notes")

    issued = exa_warnings(caught)
    assert len(issued) == 1
    assert issued[0].filename == __file__


@pytest.mark.asyncio
async def test_async_search_issues_exa_warnings_at_the_calling_line():
    ax = AsyncExa(API_KEY)
    response = httpx.Response(200, json=search_payload(ignored("a")))

    with patch.object(ax.client, "post", new=AsyncMock(return_value=response)):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            await ax.search("rust release notes")

    issued = exa_warnings(caught)
    assert [(w.message.endpoint, w.message.method, w.message.request_id) for w in issued] == [
        ("/search", "POST", "req-1")
    ]
    assert issued[0].filename == __file__


def test_stream_search_issues_exa_warnings_while_iterating():
    exa = Exa(API_KEY)
    lines = [
        'data: {"requestId":"req-9","type":"results","results":[],"warnings":[{"code":"IGNORED_FIELD",'
        '"path":"/streamed","message":"streamed is ignored."}]}',
        "data: [DONE]",
    ]

    with patch.object(exa, "request", return_value=_FakeStreamResponse(lines)):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            chunks = list(exa.stream_search("rust release notes"))

    issued = exa_warnings(caught)
    assert [str(w.message) for w in issued] == ["[exa] POST /search IGNORED_FIELD at /streamed: streamed is ignored."]
    assert issued[0].message.request_id == "req-9"
    assert issued[0].filename == __file__
    assert chunks[0].warnings == [issued[0].message.warning]


def test_deprecated_options_issue_deprecation_warnings_at_the_calling_line():
    exa = Exa(API_KEY)

    with patch("exa_py.api.requests.post", return_value=_http_response(search_payload())):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            exa.search(
                "rust release notes",
                start_crawl_date="2026-01-01",
                contents={"highlights": {"num_sentences": 2, "highlights_per_url": 3}},
            )

    deprecations = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert [str(w.message) for w in deprecations] == [
        "start_crawl_date is deprecated and will be removed in a future release. Remove it from the request.",
        "highlights num_sentences is deprecated. Use max_characters instead.",
        "highlights highlights_per_url is deprecated. Use max_characters instead.",
    ]
    assert {w.filename for w in deprecations} == {__file__}


def test_deprecated_fields_sent_through_extra_body_issue_deprecation_warnings():
    exa = Exa(API_KEY)

    with patch("exa_py.api.requests.post", return_value=_http_response(search_payload())):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            exa.search(
                "rust release notes",
                extra_body={"contents": {"highlights": {"numSentences": 2}}},
            )

    assert deprecation_messages(caught) == ["highlights num_sentences is deprecated. Use max_characters instead."]


def test_deprecated_option_replaced_by_extra_body_issues_no_deprecation_warning():
    exa = Exa(API_KEY)

    with patch("exa_py.api.requests.post", return_value=_http_response(search_payload())):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            exa.search(
                "rust release notes",
                contents={"highlights": {"num_sentences": 2}},
                extra_body={"contents": {"highlights": {"maxCharacters": 500}}},
            )

    assert deprecation_messages(caught) == []


def test_get_contents_warns_on_top_level_deprecated_highlights_options():
    exa = Exa(API_KEY)

    with patch("exa_py.api.requests.post", return_value=_http_response(search_payload())):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            exa.get_contents(["http://example.com"], highlights={"num_sentences": 2})

    assert deprecation_messages(caught) == ["highlights num_sentences is deprecated. Use max_characters instead."]


LIVECRAWL_DEPRECATION = "livecrawl is deprecated. Use max_age_hours instead. It cannot be combined with max_age_hours."


def test_livecrawl_issues_a_deprecation_warning_naming_max_age_hours():
    exa = Exa(API_KEY)

    with patch("exa_py.api.requests.post", return_value=_http_response(search_payload())):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            exa.get_contents(["http://example.com"], livecrawl="always")
            exa.search("rust release notes", contents={"text": True, "livecrawl": "always"})
            exa.search("rust release notes", contents={"text": True, "max_age_hours": 0})

    assert deprecation_messages(caught) == [LIVECRAWL_DEPRECATION, LIVECRAWL_DEPRECATION]
    assert {w.filename for w in caught if issubclass(w.category, DeprecationWarning)} == {__file__}


def test_current_options_issue_no_deprecation_warning():
    exa = Exa(API_KEY)

    with patch("exa_py.api.requests.post", return_value=_http_response(search_payload())):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            exa.search("rust release notes", contents={"highlights": {"max_characters": 500}})

    assert deprecation_messages(caught) == []


@pytest.mark.asyncio
async def test_async_deprecated_options_issue_deprecation_warnings_at_the_calling_line():
    ax = AsyncExa(API_KEY)
    response = httpx.Response(200, json=search_payload())

    with patch.object(ax.client, "post", new=AsyncMock(return_value=response)):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            await ax.search("rust release notes", end_crawl_date="2026-01-01")

    deprecations = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert [str(w.message) for w in deprecations] == [
        "end_crawl_date is deprecated and will be removed in a future release. Remove it from the request."
    ]
    assert deprecations[0].filename == __file__


def test_exa_warning_round_trips_through_pickle():
    warning = ExaWarning(ApiWarning(**ignored("a")), "/search", "POST", "req-1")

    restored = pickle.loads(pickle.dumps(warning))

    assert str(restored) == str(warning)
    assert (restored.warning, restored.endpoint, restored.method, restored.request_id) == (
        warning.warning,
        "/search",
        "POST",
        "req-1",
    )
