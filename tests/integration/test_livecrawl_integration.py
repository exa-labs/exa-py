"""Integration tests for livecrawl functionality."""

import pytest


@pytest.mark.timeout(30)
def test_get_contents_livecrawl_returns_statuses(exa):
    """Verify get_contents with livecrawl='always' returns status information."""
    url = "https://openai.com"

    response = exa.get_contents(urls=url, text=True, livecrawl="always")

    # Basic assertions - ensure call succeeds and statuses exist
    assert len(response.results) > 0
    assert response.statuses is not None
    assert len(response.statuses) > 0


@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_async_get_contents_livecrawl_returns_statuses(async_exa):
    """Verify async get_contents with livecrawl='always' returns status information."""
    url = "https://openai.com"

    response = await async_exa.get_contents(urls=url, text=True, livecrawl="always")

    # Basic assertions - ensure call succeeds and statuses exist
    assert len(response.results) > 0
    assert response.statuses is not None
    assert len(response.statuses) > 0
