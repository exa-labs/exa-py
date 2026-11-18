"""Integration tests for EXA_API_KEY environment fallback."""

import hmac
import os

import pytest

from exa_py import AsyncExa, Exa


def require_exa_api_key() -> str:
    api_key = os.getenv("EXA_API_KEY")
    if not api_key:
        pytest.skip("EXA_API_KEY environment variable not set")
    return api_key


def test_exa_uses_environment_api_key_for_live_search():
    """Verify Exa() authenticates live requests with EXA_API_KEY."""
    api_key = require_exa_api_key()
    exa = Exa()

    assert hmac.compare_digest(exa.headers["x-api-key"], api_key)

    response = exa.search("Exa AI", num_results=1, contents=False)

    assert len(response.results) > 0


@pytest.mark.asyncio
async def test_async_exa_uses_environment_api_key_for_live_search():
    """Verify AsyncExa() authenticates live requests with EXA_API_KEY."""
    api_key = require_exa_api_key()
    exa = AsyncExa()

    assert hmac.compare_digest(exa.headers["x-api-key"], api_key)

    try:
        response = await exa.search("Exa AI", num_results=1, contents=False)

        assert len(response.results) > 0
    finally:
        if exa._client is not None:
            await exa._client.aclose()
