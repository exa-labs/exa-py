"""Every Research API method fails at once, without sending a request."""

from unittest.mock import AsyncMock, patch

import pytest

from exa_py import AsyncExa, Exa
from exa_py.research.base import RESEARCH_RETIRED_MESSAGE

API_KEY = "test-key"

SYNC_CALLS = [
    lambda exa: exa.research.create(instructions="Find sources"),
    lambda exa: exa.research.get("research_1"),
    lambda exa: exa.research.get("research_1", stream=True),
    lambda exa: exa.research.list(),
    lambda exa: exa.research.poll_until_finished("research_1"),
]

ASYNC_CALLS = [
    lambda exa: exa.research.create(instructions="Find sources"),
    lambda exa: exa.research.get("research_1"),
    lambda exa: exa.research.get("research_1", stream=True),
    lambda exa: exa.research.list(),
    lambda exa: exa.research.poll_until_finished("research_1"),
]


def test_message_names_the_replacement():
    assert "retired" in RESEARCH_RETIRED_MESSAGE
    assert "exa.agent.runs.create" in RESEARCH_RETIRED_MESSAGE


@pytest.mark.parametrize("call", SYNC_CALLS)
def test_sync_research_methods_raise_without_a_request(call):
    exa = Exa(API_KEY)
    with patch.object(exa, "request") as request:
        with pytest.raises(ValueError) as exc:
            call(exa)

    assert str(exc.value) == RESEARCH_RETIRED_MESSAGE
    request.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("call", ASYNC_CALLS)
async def test_async_research_methods_raise_without_a_request(call):
    exa = AsyncExa(API_KEY)
    with patch.object(exa, "async_request", new=AsyncMock()) as request:
        with pytest.raises(ValueError) as exc:
            await call(exa)

    assert str(exc.value) == RESEARCH_RETIRED_MESSAGE
    request.assert_not_awaited()


def test_poll_raises_once_instead_of_retrying():
    exa = Exa(API_KEY)
    with patch("time.sleep") as sleep:
        with pytest.raises(ValueError, match="retired"):
            exa.research.poll_until_finished("research_1", poll_interval=1)

    sleep.assert_not_called()
