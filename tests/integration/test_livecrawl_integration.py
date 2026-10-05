"""Integration tests for livecrawl functionality.

``livecrawl="always"`` may answer from a crawl made moments earlier for the
same URL, so the crawl tests ask for a URL no earlier run has fetched.
"""

import uuid

import pytest

FIXTURE_URL = "https://example.com"


def uncrawled_url() -> str:
    """A fixture URL with a fresh query string, so no recent crawl can answer it."""
    return f"{FIXTURE_URL}/?exa-sdk-livecrawl={uuid.uuid4().hex}"


def single_status(response):
    """The one per-URL status of a single-URL ``get_contents`` call."""
    assert response.statuses is not None
    assert len(response.statuses) == 1
    return response.statuses[0]


@pytest.mark.timeout(30)
def test_get_contents_livecrawl_always_crawls(exa):
    """``livecrawl='always'`` fetches the page live and reports it as crawled."""
    url = uncrawled_url()

    response = exa.get_contents(urls=url, text=True, livecrawl="always")

    status = single_status(response)
    assert status.id == url
    assert status.status == "success"
    assert status.source == "crawled"


@pytest.mark.timeout(30)
def test_get_contents_livecrawl_never_reads_the_cache(exa):
    """``livecrawl='never'`` answers from the index and reports it as cached."""
    response = exa.get_contents(urls=FIXTURE_URL, text=True, livecrawl="never")

    status = single_status(response)
    assert status.status == "success"
    assert status.source == "cached"
    assert len(response.results) == 1


@pytest.mark.timeout(30)
def test_search_forwards_livecrawl_which_the_api_refuses_with_max_age_hours(exa):
    """search() sends contents ``livecrawl``; the API refuses it alongside ``maxAgeHours``."""
    with pytest.raises(
        ValueError, match="Cannot set both 'livecrawl' and 'maxAgeHours'"
    ):
        exa.search(
            "example domain",
            num_results=1,
            contents={"livecrawl": "always", "max_age_hours": 1},
        )


@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_async_get_contents_livecrawl_always_crawls(async_exa):
    """Async ``livecrawl='always'`` fetches the page live and reports it as crawled."""
    url = uncrawled_url()

    response = await async_exa.get_contents(urls=url, text=True, livecrawl="always")

    status = single_status(response)
    assert status.id == url
    assert status.status == "success"
    assert status.source == "crawled"


@pytest.mark.asyncio
@pytest.mark.timeout(30)
async def test_async_get_contents_livecrawl_never_reads_the_cache(async_exa):
    """Async ``livecrawl='never'`` answers from the index and reports it as cached."""
    response = await async_exa.get_contents(
        urls=FIXTURE_URL, text=True, livecrawl="never"
    )

    status = single_status(response)
    assert status.status == "success"
    assert status.source == "cached"
