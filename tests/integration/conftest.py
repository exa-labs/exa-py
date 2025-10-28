"""Shared fixtures for integration tests."""

import os
import pytest
from exa_py import Exa, AsyncExa


@pytest.fixture
def exa():
    """Fixture that provides an Exa client with real API key."""
    api_key = os.getenv("EXA_API_KEY")
    if not api_key:
        pytest.skip("EXA_API_KEY environment variable not set")
    return Exa(api_key)


@pytest.fixture
def async_exa():
    """Fixture that provides an AsyncExa client with real API key."""
    api_key = os.getenv("EXA_API_KEY")
    if not api_key:
        pytest.skip("EXA_API_KEY environment variable not set")
    return AsyncExa(api_key)
