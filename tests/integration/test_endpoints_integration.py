"""Endpoint smoke checks for search, find_similar and get_contents."""

import pytest

from exa_py import api as exa_api


# ---- Core endpoint smoke checks ----


def test_get_contents_livecrawl_preferred(exa):
    resp = exa.get_contents(
        urls=["https://techcrunch.com"], text=True, livecrawl="preferred"
    )
    assert isinstance(resp, exa_api.SearchResponse)
    # statuses may be empty when cached – still fine
    assert len(resp.results) >= 1


def test_search_and_contents(exa):
    resp = exa.search_and_contents("openai", num_results=1, text=True)
    assert resp.results and resp.results[0].text


def test_search_with_user_location(exa):
    resp = exa.search("news", num_results=1, user_location="US")
    assert resp.results


def test_find_similar(exa):
    with pytest.warns(DeprecationWarning, match="find_similar"):
        resp = exa.find_similar("https://example.com", num_results=1)
    assert resp.results


def test_get_contents_sync(exa):
    resp = exa.get_contents(urls=["https://example.com"], text=True, livecrawl="never")
    assert resp.results


@pytest.mark.asyncio
async def test_get_contents_async(async_exa):
    try:
        resp = await async_exa.get_contents(
            urls=["https://example.com"], text=True, livecrawl="never"
        )
        assert resp.results
    finally:
        if async_exa._client is not None:
            await async_exa._client.aclose()


# ---- Deprecated context compatibility / statuses ----


def test_search_and_contents_context(exa):
    """Deprecated context=True compatibility should return a context string."""
    resp = exa.search_and_contents(
        "openai research",
        num_results=3,
        context=True,  # DEPRECATED FIELD: use highlights or text.
        text=False,
    )
    assert (
        resp.context is not None  # DEPRECATED FIELD: legacy context response.
        and isinstance(resp.context, str)
        and len(resp.context) > 0
    )


def test_find_similar_and_contents_context(exa):
    """Deprecated context=True compatibility should include the context field."""
    resp = exa.find_similar_and_contents(
        "https://example.com",
        num_results=3,
        context=True,  # DEPRECATED FIELD: use highlights or text.
        text=False,
    )
    # DEPRECATED FIELD: context may be empty, but legacy attribute should exist.
    assert hasattr(resp, "context")


def test_get_contents_statuses(exa):
    """get_contents should expose statuses list (possibly empty)."""
    resp = exa.get_contents(
        urls=["https://techcrunch.com"], text=True, livecrawl="never"
    )
    # statuses attribute exists; ensure it's a list
    assert isinstance(resp.statuses, list)


# ---- Highlights ----


def test_search_with_highlights(exa):
    """search with highlights option should return highlights in results."""
    resp = exa.search(
        "openai research",
        contents={"highlights": True},
        num_results=2,
    )
    assert isinstance(resp, exa_api.SearchResponse)
    assert len(resp.results) > 0
    # At least one result should have highlights
    has_highlights = any(r.highlights is not None for r in resp.results)
    assert has_highlights, "Expected at least one result with highlights"


def test_search_with_highlights_options(exa):
    """Deprecated highlight count fields should still work for compatibility."""
    resp = exa.search(
        "machine learning",
        contents={
            "highlights": {
                "num_sentences": 2,  # DEPRECATED FIELD: use max_characters.
                "highlights_per_url": 3,  # DEPRECATED FIELD: use max_characters.
            }
        },
        num_results=2,
    )
    assert isinstance(resp, exa_api.SearchResponse)
    assert len(resp.results) > 0


def test_search_and_contents_with_highlights(exa):
    """search_and_contents with highlights option should return highlights."""
    resp = exa.search_and_contents(
        "artificial intelligence",
        highlights=True,
        num_results=2,
    )
    assert isinstance(resp, exa_api.SearchResponse)
    assert len(resp.results) > 0
    # At least one result should have highlights
    has_highlights = any(r.highlights is not None for r in resp.results)
    assert has_highlights, "Expected at least one result with highlights"
