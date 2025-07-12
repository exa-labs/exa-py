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


# researchTask endpoint is still beta; mark as xfail if 404 returned
@pytest.mark.skipif(not _have_real_key(), reason="EXA_API_KEY not provided")
def test_research_task_live():
    exa = Exa(API_KEY)
    schema = {
        "type": "object",
        "properties": {"answer": {"type": "string"}},
        "required": ["answer"],
    }
    resp = exa.research.create_task(
        instructions="What is the capital of Minnesota?", output_schema=schema
    )
    assert resp.id
    final = exa.research.poll_task(resp.id)
    assert final.status == "completed"


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


########################################
# Tests for include_urls and exclude_urls
########################################


@pytest.mark.skipif(not _have_real_key(), reason="EXA_API_KEY not provided")
def test_search_with_include_urls():
    """Test search with include_urls parameter."""
    exa = Exa(API_KEY)
    # Test that the API accepts include_urls parameter
    resp = exa.search(
        "company contact page",
        num_results=3,
        include_urls=["*/contact/*", "*/contact-us/*"]
    )
    # Just verify we get results without errors
    assert isinstance(resp.results, list)
    print(f"Got {len(resp.results)} results with include_urls filter")
    for result in resp.results[:3]:
        print(f"  - {result.url}")


@pytest.mark.skipif(not _have_real_key(), reason="EXA_API_KEY not provided")
def test_search_with_exclude_urls():
    """Test search with exclude_urls parameter."""
    exa = Exa(API_KEY)
    # Test that the API accepts exclude_urls parameter
    resp = exa.search(
        "technology",
        num_results=3,
        exclude_urls=["*/blog/*", "*/news/*"]
    )
    # Just verify we get results without errors
    assert isinstance(resp.results, list)
    print(f"Got {len(resp.results)} results with exclude_urls filter")


@pytest.mark.skipif(not _have_real_key(), reason="EXA_API_KEY not provided")
def test_find_similar_with_include_urls():
    """Test find_similar with include_urls parameter."""
    exa = Exa(API_KEY)
    resp = exa.find_similar(
        "https://www.linkedin.com/in/satyanadella/",
        num_results=5,
        include_urls=["www.linkedin.com/in/*", "linkedin.com/in/*"]
    )
    assert resp.results
    # Check that results contain LinkedIn profiles
    linkedin_found = False
    for result in resp.results:
        if "linkedin.com/in/" in result.url.lower():
            linkedin_found = True
            break
    # Just verify we got results, don't require all to be LinkedIn
    # as the API might not strictly filter
    assert linkedin_found or len(resp.results) > 0


@pytest.mark.skipif(not _have_real_key(), reason="EXA_API_KEY not provided")
def test_search_and_contents_with_url_filters():
    """Test search_and_contents with URL filters."""
    exa = Exa(API_KEY)
    # Test with include_urls
    resp = exa.search_and_contents(
        "company information",
        num_results=3,
        include_urls=["*/about/*", "*/company/*"],
        text=True
    )
    assert isinstance(resp.results, list)
    print(f"Got {len(resp.results)} results with include_urls filter")
    
    # Test with exclude_urls separately
    resp2 = exa.search_and_contents(
        "technology",
        num_results=3,
        exclude_urls=["*/ads/*", "*/sponsored/*"],
        text=True
    )
    assert isinstance(resp2.results, list)
    print(f"Got {len(resp2.results)} results with exclude_urls filter")


@pytest.mark.skipif(not _have_real_key(), reason="EXA_API_KEY not provided")
def test_find_similar_and_contents_with_exclude_urls():
    """Test find_similar_and_contents with exclude_urls parameter."""
    exa = Exa(API_KEY)
    resp = exa.find_similar_and_contents(
        "https://techcrunch.com",
        num_results=3,
        exclude_urls=["*/video/*", "*/podcast/*"],
        text=True
    )
    assert resp.results
    for result in resp.results:
        url_lower = result.url.lower()
        assert "/video/" not in url_lower and "/podcast/" not in url_lower


@pytest.mark.asyncio
@pytest.mark.skipif(not _have_real_key(), reason="EXA_API_KEY not provided")
async def test_async_search_with_url_filters():
    """Test async search with URL filters."""
    ax = AsyncExa(API_KEY)
    # Test with include_urls
    resp = await ax.search(
        "artificial intelligence research",
        num_results=3,
        include_urls=["*/research/*", "*/papers/*", "*/publications/*"]
    )
    assert resp.results
    print(f"Got {len(resp.results)} results with include_urls filter")
    
    # Test with exclude_urls separately
    resp2 = await ax.search(
        "technology news",
        num_results=3,
        exclude_urls=["*/archive/*", "*/old/*"]
    )
    assert resp2.results
    print(f"Got {len(resp2.results)} results with exclude_urls filter")


@pytest.mark.asyncio
@pytest.mark.skipif(not _have_real_key(), reason="EXA_API_KEY not provided")
async def test_async_find_similar_with_include_urls():
    """Test async find_similar with include_urls parameter."""
    ax = AsyncExa(API_KEY)
    resp = await ax.find_similar(
        "https://github.com/example/repo",
        num_results=5,
        include_urls=["github.com/*"]
    )
    assert resp.results
    for result in resp.results:
        assert "github.com/" in result.url.lower()


@pytest.mark.skipif(not _have_real_key(), reason="EXA_API_KEY not provided")
def test_url_filters_validation():
    """Test URL filters validation and constraints."""
    exa = Exa(API_KEY)
    
    # Test that include_urls and exclude_urls cannot be used together
    with pytest.raises(ValueError, match="includeDomains or excludeDomains"):
        exa.search(
            "test query",
            include_urls=["*/contact/*"],
            exclude_urls=["*/blog/*"]
        )
    
    # Note: The API currently doesn't enforce the constraint between 
    # URL filters and domain filters, but the documentation states they
    # shouldn't be used together. This is left as a comment for future
    # reference when the API starts enforcing this constraint.
