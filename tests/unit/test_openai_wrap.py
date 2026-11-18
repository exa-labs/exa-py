"""A client `wrap` returns searches Exa when the model asks it to, for Exa and AsyncExa.

The OpenAI clients are the real ones, answered by a fake OpenAI API on an
in-process transport; the Exa search is stubbed.
"""

import json
from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock

import httpx
import pytest
from openai import AsyncOpenAI, OpenAI

from exa_py import AsyncExa, Exa

CLIENTS = [pytest.param(False, id="sync"), pytest.param(True, id="async")]
OPENAI_ARGS: Dict[str, Any] = {"api_key": "test", "base_url": "http://openai.test/v1", "max_retries": 0}
QUESTION = [{"role": "user", "content": "What happened to Alpha?"}]

SEARCH_RESPONSE = {
    "requestId": "req-1",
    "resolvedSearchType": "neural",
    "results": [
        {"id": "https://example.com/a", "url": "https://example.com/a", "title": "Alpha", "text": "Alpha text"}
    ],
}


def completion(**message: Any) -> Dict[str, Any]:
    """A chat completion as the OpenAI API sends it, its one choice holding `message`."""
    return {
        "id": "chatcmpl-1",
        "object": "chat.completion",
        "created": 0,
        "model": "gpt-test",
        "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", **message}}],
    }


SEARCH_CALL = completion(
    content=None,
    tool_calls=[
        {
            "id": "call-1",
            "type": "function",
            "function": {"name": "search", "arguments": '{"query": "alpha news"}'},
        }
    ],
)
ANSWER = completion(content="Alpha was acquired.")


class FakeOpenAIApi:
    """Answers each chat completion request with the next reply, keeping the request bodies."""

    def __init__(self, *replies: Dict[str, Any]) -> None:
        self.replies = list(replies)
        self.requests: List[Dict[str, Any]] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(json.loads(request.content))
        return httpx.Response(200, json=self.replies.pop(0))


def wrapped(asynchronous: bool, api: FakeOpenAIApi):
    """An Exa client with a stubbed search, and the OpenAI client it wrapped."""
    transport = httpx.MockTransport(api)
    if asynchronous:
        exa = AsyncExa("test-key")
        exa.async_request = AsyncMock(return_value=SEARCH_RESPONSE)
        client = AsyncOpenAI(http_client=httpx.AsyncClient(transport=transport), **OPENAI_ARGS)
    else:
        exa = Exa("test-key")
        exa.request = Mock(return_value=SEARCH_RESPONSE)
        client = OpenAI(http_client=httpx.Client(transport=transport), **OPENAI_ARGS)
    return exa, exa.wrap(client)


async def ask(asynchronous: bool, client: Any, **kwargs: Any) -> Any:
    """The wrapped client's answer to QUESTION, awaited for the async client."""
    reply = client.chat.completions.create(model="gpt-test", messages=QUESTION, **kwargs)
    return await reply if asynchronous else reply


@pytest.mark.parametrize("asynchronous", CLIENTS)
async def test_answers_with_the_search_the_model_asked_for(asynchronous):
    api = FakeOpenAIApi(SEARCH_CALL, ANSWER)
    exa, client = wrapped(asynchronous, api)

    reply = await ask(asynchronous, client, num_results=2, include_domains=["example.com"])

    assert reply.choices[0].message.content == "Alpha was acquired."
    assert [result.url for result in reply.exa_result.results] == ["https://example.com/a"]
    assert api.requests[0]["tools"][0]["function"]["name"] == "search"
    search = (exa.async_request if asynchronous else exa.request).call_args.args[1]
    assert (search["query"], search["numResults"], search["includeDomains"]) == ("alpha news", 2, ["example.com"])
    tool_message = api.requests[1]["messages"][-1]
    assert (tool_message["role"], tool_message["tool_call_id"]) == ("tool", "call-1")
    assert "Alpha text" in tool_message["content"]


@pytest.mark.parametrize("asynchronous", CLIENTS)
async def test_does_not_search_when_the_model_answers_directly(asynchronous):
    api = FakeOpenAIApi(ANSWER)
    exa, client = wrapped(asynchronous, api)

    reply = await ask(asynchronous, client)

    assert reply.choices[0].message.content == "Alpha was acquired."
    assert reply.exa_result is None
    assert len(api.requests) == 1
    assert not (exa.async_request if asynchronous else exa.request).called


def test_async_exa_answers_through_a_sync_client_without_await_when_the_model_does_not_search():
    api = FakeOpenAIApi(ANSWER)
    exa = AsyncExa("test-key")
    exa.async_request = AsyncMock(return_value=SEARCH_RESPONSE)
    client = exa.wrap(OpenAI(http_client=httpx.Client(transport=httpx.MockTransport(api)), **OPENAI_ARGS))

    reply = client.chat.completions.create(model="gpt-test", messages=QUESTION)

    assert reply.choices[0].message.content == "Alpha was acquired."
    assert reply.exa_result is None
    assert not exa.async_request.called


@pytest.mark.parametrize("asynchronous", CLIENTS)
async def test_use_exa_none_tells_the_model_not_to_search(asynchronous):
    api = FakeOpenAIApi(ANSWER)
    exa, client = wrapped(asynchronous, api)

    reply = await ask(asynchronous, client, use_exa="none")

    assert reply.exa_result is None
    assert api.requests[0]["tool_choice"] == "none"
    assert not (exa.async_request if asynchronous else exa.request).called


@pytest.mark.parametrize("asynchronous", CLIENTS)
async def test_use_exa_required_makes_the_model_search_then_lets_it_answer(asynchronous):
    api = FakeOpenAIApi(SEARCH_CALL, ANSWER)
    _, client = wrapped(asynchronous, api)

    reply = await ask(asynchronous, client, use_exa="required")

    assert reply.choices[0].message.content == "Alpha was acquired."
    assert (api.requests[0]["tool_choice"], api.requests[0]["parallel_tool_calls"]) == ("required", False)
    assert api.requests[1]["tool_choice"] == "none"


@pytest.mark.parametrize("asynchronous", CLIENTS)
async def test_use_exa_auto_lets_the_model_choose_then_makes_it_answer(asynchronous):
    api = FakeOpenAIApi(SEARCH_CALL, ANSWER)
    _, client = wrapped(asynchronous, api)

    await ask(asynchronous, client)

    assert "tool_choice" not in api.requests[0]
    assert "parallel_tool_calls" not in api.requests[0]
    assert api.requests[1]["tool_choice"] == "none"
