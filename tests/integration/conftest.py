"""Shared fixtures for integration tests.

The suite runs against the hosted API when ``EXA_API_KEY`` is set and skips
otherwise. ``EXA_BASE_URL`` points the clients at another server.

``pytest tests/integration --fake-api`` runs the suite offline instead: it
starts the local fake API server (``fake_api.py``) on a loopback port and
points ``EXA_BASE_URL`` and ``EXA_API_KEY`` at it for the whole session.
"""

import os

import pytest
from exa_py import Exa, AsyncExa

from .environment import client_args
from .fake_api import FakeExaApi

_FAKE_API = pytest.StashKey[FakeExaApi]()
_SAVED_ENVIRONMENT = pytest.StashKey[dict]()
_FAKE_API_ENVIRONMENT = ("EXA_BASE_URL", "EXA_API_KEY")


def pytest_addoption(parser):
    parser.addoption(
        "--fake-api",
        action="store_true",
        default=False,
        help="Run the integration tests against the local fake API server.",
    )


def pytest_configure(config):
    if not config.getoption("--fake-api"):
        return
    api = FakeExaApi().start()
    config.stash[_FAKE_API] = api
    config.stash[_SAVED_ENVIRONMENT] = {
        name: os.environ.get(name) for name in _FAKE_API_ENVIRONMENT
    }
    os.environ["EXA_BASE_URL"] = api.url
    os.environ["EXA_API_KEY"] = api.api_key


def pytest_unconfigure(config):
    api = config.stash.get(_FAKE_API, None)
    if api is None:
        return
    api.stop()
    for name, value in config.stash[_SAVED_ENVIRONMENT].items():
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value


@pytest.fixture(autouse=True)
def _offline_runs_stay_on_the_fake_api(request):
    """Under ``--fake-api``, fails any test whose client would leave the fake server."""
    api = request.config.stash.get(_FAKE_API, None)
    if api is not None and os.environ.get("EXA_BASE_URL") != api.url:
        pytest.fail("EXA_BASE_URL no longer points at the local fake API server")


@pytest.fixture
def exa():
    """Fixture that provides an Exa client for the configured API."""
    api_key = os.getenv("EXA_API_KEY")
    if not api_key:
        pytest.skip("EXA_API_KEY environment variable not set")
    return Exa(*client_args(api_key))


@pytest.fixture
def async_exa():
    """Fixture that provides an AsyncExa client for the configured API."""
    api_key = os.getenv("EXA_API_KEY")
    if not api_key:
        pytest.skip("EXA_API_KEY environment variable not set")
    return AsyncExa(*client_args(api_key))
