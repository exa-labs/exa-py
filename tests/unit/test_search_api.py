import os
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from exa_py import Exa, AsyncExa, api as exa_api

API_KEY = os.getenv("EXA_API_KEY", "test-key")


def _have_real_key() -> bool:
    return API_KEY != "test-key" and len(API_KEY) > 10


########################################
# Offline unit tests (no network)
########################################


def test_contentstatus_parsing_offline():
    payload_status = {"id": "u", "status": "success", "source": "cached"}
    cs = exa_api.ContentStatus(**payload_status)
    assert cs.id == "u" and cs.status == "success" and cs.source == "cached"


def test_answerresponse_accepts_dict():
    dummy = exa_api.AnswerResult(id="1", url="u", title="t")
    resp = exa_api.AnswerResponse(answer={"foo": "bar"}, citations=[dummy])
    assert isinstance(resp.answer, dict) and resp.answer["foo"] == "bar"


def test_search_accepts_user_location_offline():
    """Test that search method accepts user_location parameter without error."""
    exa = Exa(API_KEY)
    # Create a mock response
    mock_response = {
        "results": [{"url": "http://example.com", "id": "1", "title": "Test"}],
        "costDollars": {"total": 0.001},
    }

    with patch.object(exa, "request", return_value=mock_response):
        # This should not raise any errors about unknown parameters
        resp = exa.search("test query", user_location="US", num_results=1)
        assert isinstance(resp, exa_api.SearchResponse)


def test_search_accepts_additional_queries_offline():
    """Test that search method accepts additional_queries parameter for deep search.
    
    Deep search always returns context in the response.
    """
    exa = Exa(API_KEY)
    # Create a mock response with context (always returned for deep search)
    mock_response = {
        "results": [
            {"url": "http://example.com", "id": "1", "title": "Deep Search Result"}
        ],
        "context": "Deep search context string",
        "costDollars": {"total": 0.002},
    }

    with patch.object(exa, "request", return_value=mock_response) as mock_request:
        # Test with additional_queries for deep search
        resp = exa.search(
            "machine learning",
            type="deep",
            additional_queries=["ML algorithms", "neural networks", "AI models"],
            num_results=5,
        )
        assert isinstance(resp, exa_api.SearchResponse)
        assert resp.context is not None  # Context always present for deep search
        
        # Verify the request was called with correct camelCase parameters
        call_args = mock_request.call_args
        assert call_args[0][0] == "/search"
        options = call_args[0][1]
        assert "additionalQueries" in options
        assert options["additionalQueries"] == ["ML algorithms", "neural networks", "AI models"]
        assert options["type"] == "deep"


@pytest.mark.asyncio
async def test_async_request_accepts_201():
    ax = AsyncExa(API_KEY)

    async def _fake_post(url, json, headers):
        return httpx.Response(201, json={"ok": True})

    with patch.object(ax.client, "post", new=AsyncMock(side_effect=_fake_post)):
        data = await ax.async_request("/dummy", {})
    assert data == {"ok": True}


########################################
# Live integration tests (skipped without key)
########################################


@pytest.mark.skipif(not _have_real_key(), reason="EXA_API_KEY not provided")
def test_user_agent_header():
    exa = Exa(API_KEY)
    # Get the expected version dynamically
    expected_version = exa_api._get_package_version()
    expected_user_agent = f"exa-py {expected_version}"
    assert exa.headers["User-Agent"] == expected_user_agent


@pytest.mark.skipif(not _have_real_key(), reason="EXA_API_KEY not provided")
def test_research_client_attrs():
    exa = Exa(API_KEY)
    aexa = AsyncExa(API_KEY)
    assert hasattr(exa, "research") and hasattr(aexa, "research")


# ---- Core live endpoint smoke checks ----


@pytest.mark.skipif(not _have_real_key(), reason="EXA_API_KEY not provided")
def test_get_contents_live_preferred():
    exa = Exa(API_KEY)
    resp = exa.get_contents(
        urls=["https://techcrunch.com"], text=True, livecrawl="preferred"
    )
    assert isinstance(resp, exa_api.SearchResponse)
    # statuses may be empty when cached – still fine
    assert len(resp.results) >= 1


@pytest.mark.skipif(not _have_real_key(), reason="EXA_API_KEY not provided")
def test_search_and_contents_live():
    exa = Exa(API_KEY)
    resp = exa.search_and_contents("openai", num_results=1, text=True)
    assert resp.results and resp.results[0].text


@pytest.mark.skipif(not _have_real_key(), reason="EXA_API_KEY not provided")
def test_search_with_user_location_live():
    exa = Exa(API_KEY)
    resp = exa.search("news", num_results=1, user_location="US")
    assert resp.results


@pytest.mark.skipif(not _have_real_key(), reason="EXA_API_KEY not provided")
def test_find_similar_live():
    exa = Exa(API_KEY)
    resp = exa.find_similar("https://www.openai.com", num_results=1)
    assert resp.results


@pytest.mark.skipif(not _have_real_key(), reason="EXA_API_KEY not provided")
def test_get_contents_sync_live():
    exa = Exa(API_KEY)
    resp = exa.get_contents(urls=["https://example.com"], text=True, livecrawl="never")
    assert resp.results


@pytest.mark.asyncio
@pytest.mark.skipif(not _have_real_key(), reason="EXA_API_KEY not provided")
async def test_get_contents_async_live():
    ax = AsyncExa(API_KEY)
    resp = await ax.get_contents(
        urls=["https://example.com"], text=True, livecrawl="never"
    )
    assert resp.results


########################################
# Live tests for new context / statuses features
########################################


@pytest.mark.skipif(not _have_real_key(), reason="EXA_API_KEY not provided")
def test_search_and_contents_context_live():
    """search_and_contents with context=True should return non-empty context string."""
    exa = Exa(API_KEY)
    resp = exa.search_and_contents(
        "openai research", num_results=3, context=True, text=False
    )
    assert (
        resp.context is not None
        and isinstance(resp.context, str)
        and len(resp.context) > 0
    )


@pytest.mark.skipif(not _have_real_key(), reason="EXA_API_KEY not provided")
def test_find_similar_and_contents_context_live():
    """find_similar_and_contents with context flag should include context string."""
    exa = Exa(API_KEY)
    resp = exa.find_similar_and_contents(
        "https://www.openai.com", num_results=3, context=True, text=False
    )
    # context may be empty depending on backend, but attribute should exist (None or str)
    assert hasattr(resp, "context")


@pytest.mark.skipif(not _have_real_key(), reason="EXA_API_KEY not provided")
def test_get_contents_statuses_live():
    """get_contents should expose statuses list (possibly empty)."""
    exa = Exa(API_KEY)
    resp = exa.get_contents(
        urls=["https://techcrunch.com"], text=True, livecrawl="never"
    )
    # statuses attribute exists; ensure it's a list
    assert isinstance(resp.statuses, list)
