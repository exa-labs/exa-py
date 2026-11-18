"""The base URL ``Exa`` and ``AsyncExa`` send their requests to.

Runs against local servers, so each test sees which server every request
reached, at which path and with which ``x-api-key``.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from exa_py import AsyncExa, Exa

EU_BASE_URL = "https://api.eu.exa.ai"
CLIENTS = pytest.mark.parametrize("client_class", [Exa, AsyncExa], ids=["Exa", "AsyncExa"])


class _Api:
    """A local server that records the path and ``x-api-key`` of every request and answers with empty results."""

    def __init__(self):
        self.requests = []
        api = self

        class Handler(BaseHTTPRequestHandler):
            def _handle(self):
                length = int(self.headers.get("Content-Length", 0))
                self.rfile.read(length)
                api.requests.append((self.path, self.headers.get("x-api-key")))
                payload = json.dumps({"results": [], "data": [], "hasMore": False}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            do_GET = do_POST = _handle

            def log_message(self, *args):
                pass

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._server.daemon_threads = True
        self.url = f"http://127.0.0.1:{self._server.server_address[1]}"
        threading.Thread(
            target=self._server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True
        ).start()

    def close(self):
        self._server.shutdown()
        self._server.server_close()


def _serving():
    server = _Api()
    try:
        yield server
    finally:
        server.close()


@pytest.fixture
def first_api():
    yield from _serving()


@pytest.fixture
def second_api():
    yield from _serving()


@pytest.fixture(autouse=True)
def no_base_url_in_environment(monkeypatch):
    monkeypatch.delenv("EXA_BASE_URL", raising=False)


@CLIENTS
def test_the_default_base_url_is_the_public_api(client_class):
    assert client_class("test-key").base_url == "https://api.exa.ai"


@CLIENTS
def test_exa_base_url_sets_the_base_url_of_a_client_given_none(client_class, monkeypatch):
    monkeypatch.setenv("EXA_BASE_URL", EU_BASE_URL)

    assert client_class("test-key").base_url == EU_BASE_URL


@CLIENTS
def test_a_blank_exa_base_url_leaves_the_default(client_class, monkeypatch):
    monkeypatch.setenv("EXA_BASE_URL", "  ")

    assert client_class("test-key").base_url == "https://api.exa.ai"


@CLIENTS
def test_base_url_wins_over_exa_base_url(client_class, monkeypatch):
    monkeypatch.setenv("EXA_BASE_URL", "https://api.exa.ai")

    assert client_class("test-key", base_url=EU_BASE_URL).base_url == EU_BASE_URL


@CLIENTS
@pytest.mark.parametrize("from_environment", [False, True], ids=["argument", "EXA_BASE_URL"])
def test_trailing_slashes_are_dropped(client_class, from_environment, monkeypatch):
    if from_environment:
        monkeypatch.setenv("EXA_BASE_URL", EU_BASE_URL + "//")
        client = client_class("test-key")
    else:
        client = client_class("test-key", base_url=EU_BASE_URL + "/")

    assert client.base_url == EU_BASE_URL


def test_exa_sends_requests_below_a_base_url_with_a_trailing_slash(first_api):
    Exa("test-key", base_url=first_api.url + "/").search("test")

    assert first_api.requests == [("/search", "test-key")]


async def test_async_exa_sends_requests_below_a_base_url_with_a_trailing_slash(first_api):
    async with AsyncExa("test-key", base_url=first_api.url + "/") as exa:
        await exa.search("test")

    assert first_api.requests == [("/search", "test-key")]


def test_async_exa_takes_api_base_as_a_deprecated_name_of_base_url():
    with pytest.warns(DeprecationWarning, match="api_base is deprecated. Use base_url."):
        exa = AsyncExa("test-key", api_base=EU_BASE_URL)

    assert exa.base_url == EU_BASE_URL


def test_async_exa_refuses_base_url_and_api_base_together():
    with pytest.raises(TypeError, match="Pass base_url alone"):
        AsyncExa("test-key", base_url=EU_BASE_URL, api_base=EU_BASE_URL)


def test_clients_for_two_endpoints_each_use_their_own_base_url_and_key(first_api, second_api, monkeypatch):
    # A process-wide EXA_BASE_URL does not reach a client given its own base_url.
    monkeypatch.setenv("EXA_BASE_URL", "http://127.0.0.1:9")
    team_a = Exa("team-a-key", base_url=first_api.url)
    team_b = Exa("team-b-key", base_url=second_api.url)

    team_b.search("team b query")
    team_a.search("team a query")
    team_b.get_contents(["https://example.com"])
    team_b.websets.list()

    assert first_api.requests == [("/search", "team-a-key")]
    assert second_api.requests == [
        ("/search", "team-b-key"),
        ("/contents", "team-b-key"),
        ("/websets/v0/websets", "team-b-key"),
    ]


async def test_async_clients_for_two_endpoints_each_use_their_own_base_url_and_key(
    first_api, second_api, monkeypatch
):
    monkeypatch.setenv("EXA_BASE_URL", "http://127.0.0.1:9")
    async with AsyncExa("team-a-key", base_url=first_api.url) as team_a, AsyncExa(
        "team-b-key", base_url=second_api.url
    ) as team_b:
        await team_b.search("team b query")
        await team_a.search("team a query")
        await team_b.get_contents(["https://example.com"])
        await team_b.websets.list()

    assert first_api.requests == [("/search", "team-a-key")]
    assert second_api.requests == [
        ("/search", "team-b-key"),
        ("/contents", "team-b-key"),
        ("/websets/v0/websets", "team-b-key"),
    ]
