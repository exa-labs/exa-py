"""``user_identifier`` attributes a request to one end user of the caller's app.

These tests check that every method that calls ``/search``, ``/contents``,
``/answer`` or ``/agent/runs`` sends it as the top-level ``userIdentifier``
body field when given, and leaves it out when not. They make no HTTP calls.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from exa_py import AsyncExa, Exa
from exa_py.agent import (
    AGENT_BETA_HEADER,
    AgentNamespace,
    AsyncAgentNamespace,
    BetaClient,
)

API_KEY = "test-key"
USER_IDENTIFIER = "7f3a9c52-1d4e-4b8a-9e60-2c5d8a1f0b37"

SEARCH_RESPONSE = {"results": [], "costDollars": {"total": 0.001}}
CONTENTS_RESPONSE = {"results": [], "statuses": []}
ANSWER_RESPONSE = {"answer": "Paris", "citations": []}
AGENT_RUN = {"id": "agent_run_123", "status": "completed"}


class _FakeStreamResponse:
    status_code = 200
    text = ""

    def iter_lines(self):
        return iter(())

    async def aiter_lines(self):
        for line in ():
            yield line

    def close(self):
        return None


def _body(mock_request, call=-1):
    """The JSON body passed to the nth call of a mocked ``request``."""
    return mock_request.call_args_list[call][0][1]


########################################
# Exa
########################################


def test_search_sends_user_identifier():
    exa = Exa(API_KEY)
    with patch.object(exa, "request", return_value=SEARCH_RESPONSE) as mock_request:
        exa.search("hottest AI startups", user_identifier=USER_IDENTIFIER)
        exa.search("hottest AI startups")

    assert mock_request.call_args_list[0][0][0] == "/search"
    assert _body(mock_request, 0)["userIdentifier"] == USER_IDENTIFIER
    assert "user_identifier" not in _body(mock_request, 0)
    assert "userIdentifier" not in _body(mock_request, 1)


def test_stream_search_sends_user_identifier():
    exa = Exa(API_KEY)
    with patch.object(
        exa, "request", return_value=_FakeStreamResponse()
    ) as mock_request:
        exa.stream_search("battery breakthroughs", user_identifier=USER_IDENTIFIER)

    assert _body(mock_request)["userIdentifier"] == USER_IDENTIFIER
    assert _body(mock_request)["stream"] is True


def test_search_and_contents_keeps_user_identifier_outside_contents():
    exa = Exa(API_KEY)
    with patch.object(exa, "request", return_value=SEARCH_RESPONSE) as mock_request:
        with pytest.warns(DeprecationWarning):
            exa.search_and_contents(
                "hottest AI startups", text=True, user_identifier=USER_IDENTIFIER
            )

    body = _body(mock_request)
    assert body["userIdentifier"] == USER_IDENTIFIER
    assert body["contents"] == {"text": True}


def test_get_contents_sends_user_identifier():
    exa = Exa(API_KEY)
    with patch.object(exa, "request", return_value=CONTENTS_RESPONSE) as mock_request:
        exa.get_contents(
            ["https://example.com"], text=True, user_identifier=USER_IDENTIFIER
        )
        exa.get_contents("https://example.com")

    assert mock_request.call_args_list[0][0][0] == "/contents"
    assert _body(mock_request, 0) == {
        "urls": ["https://example.com"],
        "text": True,
        "userIdentifier": USER_IDENTIFIER,
    }
    assert "userIdentifier" not in _body(mock_request, 1)


def test_find_similar_and_contents_rejects_user_identifier():
    """/findSimilar does not take the field, so the SDK refuses it."""
    exa = Exa(API_KEY)
    with patch.object(exa, "request", return_value=SEARCH_RESPONSE) as mock_request:
        with pytest.warns(DeprecationWarning):
            with pytest.raises(ValueError, match="user_identifier"):
                exa.find_similar_and_contents(
                    "https://example.com", user_identifier=USER_IDENTIFIER
                )

    mock_request.assert_not_called()


def test_answer_sends_user_identifier():
    exa = Exa(API_KEY)
    with patch.object(exa, "request", return_value=ANSWER_RESPONSE) as mock_request:
        exa.answer("What is the capital of France?", user_identifier=USER_IDENTIFIER)
        exa.answer("What is the capital of France?")

    assert mock_request.call_args_list[0][0][0] == "/answer"
    assert _body(mock_request, 0)["userIdentifier"] == USER_IDENTIFIER
    assert "userIdentifier" not in _body(mock_request, 1)


def test_stream_answer_sends_user_identifier():
    exa = Exa(API_KEY)
    with patch.object(
        exa, "request", return_value=_FakeStreamResponse()
    ) as mock_request:
        exa.stream_answer(
            "What is the capital of France?", user_identifier=USER_IDENTIFIER
        )

    assert _body(mock_request)["userIdentifier"] == USER_IDENTIFIER
    assert _body(mock_request)["stream"] is True


########################################
# AsyncExa
########################################


@pytest.mark.asyncio
async def test_async_search_sends_user_identifier():
    exa = AsyncExa(API_KEY)
    with patch.object(
        exa, "async_request", new=AsyncMock(return_value=SEARCH_RESPONSE)
    ) as mock_request:
        await exa.search("hottest AI startups", user_identifier=USER_IDENTIFIER)
        await exa.search("hottest AI startups")

    assert _body(mock_request, 0)["userIdentifier"] == USER_IDENTIFIER
    assert "userIdentifier" not in _body(mock_request, 1)


@pytest.mark.asyncio
async def test_async_stream_search_sends_user_identifier():
    exa = AsyncExa(API_KEY)
    with patch.object(
        exa, "async_request", new=AsyncMock(return_value=_FakeStreamResponse())
    ) as mock_request:
        await exa.stream_search(
            "battery breakthroughs", user_identifier=USER_IDENTIFIER
        )

    assert _body(mock_request)["userIdentifier"] == USER_IDENTIFIER


@pytest.mark.asyncio
async def test_async_search_and_contents_sends_user_identifier():
    exa = AsyncExa(API_KEY)
    with patch.object(
        exa, "async_request", new=AsyncMock(return_value=SEARCH_RESPONSE)
    ) as mock_request:
        with pytest.warns(DeprecationWarning):
            await exa.search_and_contents(
                "hottest AI startups", text=True, user_identifier=USER_IDENTIFIER
            )

    assert _body(mock_request)["userIdentifier"] == USER_IDENTIFIER
    assert _body(mock_request)["contents"] == {"text": True}


@pytest.mark.asyncio
async def test_async_get_contents_sends_user_identifier():
    exa = AsyncExa(API_KEY)
    with patch.object(
        exa, "async_request", new=AsyncMock(return_value=CONTENTS_RESPONSE)
    ) as mock_request:
        await exa.get_contents("https://example.com", user_identifier=USER_IDENTIFIER)

    assert mock_request.call_args[0][0] == "/contents"
    assert _body(mock_request)["userIdentifier"] == USER_IDENTIFIER


@pytest.mark.asyncio
async def test_async_answer_sends_user_identifier():
    exa = AsyncExa(API_KEY)
    with patch.object(
        exa, "async_request", new=AsyncMock(return_value=ANSWER_RESPONSE)
    ) as mock_request:
        await exa.answer(
            "What is the capital of France?", user_identifier=USER_IDENTIFIER
        )

    assert _body(mock_request)["userIdentifier"] == USER_IDENTIFIER


@pytest.mark.asyncio
async def test_async_stream_answer_sends_user_identifier():
    exa = AsyncExa(API_KEY)
    with patch.object(
        exa, "async_request", new=AsyncMock(return_value=_FakeStreamResponse())
    ) as mock_request:
        await exa.stream_answer(
            "What is the capital of France?", user_identifier=USER_IDENTIFIER
        )

    assert _body(mock_request)["userIdentifier"] == USER_IDENTIFIER
    assert _body(mock_request)["stream"] is True


########################################
# Agent runs
########################################


def test_agent_run_create_sends_user_identifier():
    client = MagicMock()
    client.request.return_value = AGENT_RUN
    runs = AgentNamespace(client).runs

    runs.create(query="Find companies.", user_identifier=USER_IDENTIFIER)
    runs.create(query="Find companies.")

    first, second = client.request.call_args_list
    assert first.args == ("/agent/runs",)
    assert first.kwargs["data"] == {
        "query": "Find companies.",
        "userIdentifier": USER_IDENTIFIER,
    }
    assert "userIdentifier" not in second.kwargs["data"]


def test_agent_run_create_and_wait_sends_user_identifier():
    client = MagicMock()
    client.request.return_value = AGENT_RUN
    runs = AgentNamespace(client).runs

    runs.create_and_wait(
        query="Find companies.",
        user_identifier=USER_IDENTIFIER,
        poll_interval=5,
        timeout_ms=1000,
    )

    assert client.request.call_args_list[0].kwargs["data"] == {
        "query": "Find companies.",
        "userIdentifier": USER_IDENTIFIER,
    }


def test_beta_agent_run_create_sends_user_identifier():
    client = MagicMock()
    client.request.return_value = AGENT_RUN
    runs = BetaClient(client).agent.runs

    runs.create(
        betas=[AGENT_BETA_HEADER],
        query="Find companies.",
        user_identifier=USER_IDENTIFIER,
    )

    assert client.request.call_args.kwargs["data"] == {
        "query": "Find companies.",
        "userIdentifier": USER_IDENTIFIER,
    }


@pytest.mark.asyncio
async def test_async_agent_run_create_sends_user_identifier():
    client = MagicMock()
    client.async_request = AsyncMock(return_value=AGENT_RUN)
    runs = AsyncAgentNamespace(client).runs

    await runs.create(query="Find companies.", user_identifier=USER_IDENTIFIER)

    assert client.async_request.await_args.kwargs["data"] == {
        "query": "Find companies.",
        "userIdentifier": USER_IDENTIFIER,
    }


@pytest.mark.asyncio
async def test_async_agent_run_create_and_wait_sends_user_identifier():
    client = MagicMock()
    client.async_request = AsyncMock(return_value=AGENT_RUN)
    runs = AsyncAgentNamespace(client).runs

    await runs.create_and_wait(
        query="Find companies.",
        user_identifier=USER_IDENTIFIER,
        poll_interval=5,
        timeout_ms=1000,
    )

    assert client.async_request.await_args_list[0].kwargs["data"] == {
        "query": "Find companies.",
        "userIdentifier": USER_IDENTIFIER,
    }
