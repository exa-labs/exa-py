from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from pydantic import BaseModel, Field

from exa_py import AsyncExa, Exa
from exa_py.agent import (
    AGENT_BETA_HEADER,
    AsyncBetaClient,
    BetaClient,
    ListAgentRunsResponse,
)

AGENT_BETAS = [AGENT_BETA_HEADER]


@pytest.fixture
def mock_client():
    return MagicMock()


@pytest.fixture
def run_client(mock_client):
    return BetaClient(mock_client).agent.runs


def _make_run(run_id: str = "agent_run_123") -> dict:
    return {
        "id": run_id,
        "object": "agent_run",
        "status": "completed",
        "stopReason": "schema_satisfied",
        "createdAt": "2026-05-07T18:31:00.000Z",
        "completedAt": "2026-05-07T18:31:24.000Z",
        "request": {"query": "Find recent funding rounds."},
        "output": {
            "text": "Returned 1 company.",
            "structured": {"companies": [{"name": "Example AI"}]},
            "grounding": [
                {
                    "field": "structured.companies[0].name",
                    "citations": [{"url": "https://example.com", "title": "Example"}],
                    "score": 0.9,
                    "confidence": "high",
                }
            ],
        },
        "usage": {"agentComputeUnits": 0.1, "searches": 2},
        "costDollars": {"total": 0.02, "agentCompute": 0.01, "search": 0.01},
    }


def _make_response() -> dict:
    return {
        "id": "resp_agent_run_123",
        "object": "response",
        "created_at": 1778706660,
        "completed_at": 1778706684,
        "status": "completed",
        "model": "agent",
        "output_text": "Returned 1 company.",
        "output": [
            {
                "id": "msg_agent_run_123",
                "type": "message",
                "status": "completed",
                "role": "assistant",
                "content": [
                    {
                        "type": "output_text",
                        "text": "Returned 1 company.",
                        "annotations": [],
                    }
                ],
            }
        ],
        "error": None,
        "incomplete_details": None,
        "instructions": None,
        "previous_response_id": None,
        "metadata": {},
        "tools": [],
        "tool_choice": "auto",
        "parallel_tool_calls": True,
        "temperature": 1,
        "top_p": 1,
        "reasoning": {"effort": "minimal", "summary": None},
        "usage": None,
    }


class _MockAsyncSseResponse:
    def __init__(self, lines):
        self.lines = lines
        self.closed = False

    async def aiter_lines(self):
        for line in self.lines:
            yield line

    async def aclose(self):
        self.closed = True


class _CompanyOutput(BaseModel):
    company_name: str = Field(alias="companyName")


def test_exa_exposes_agent_run_under_beta_namespace():
    exa = Exa(api_key="test-api-key")
    assert hasattr(exa.beta.agent, "runs")
    assert not hasattr(exa.beta.agent, "run")
    assert not hasattr(exa, "agent")


def test_async_exa_exposes_agent_run_under_beta_namespace():
    exa = AsyncExa(api_key="test-api-key")
    assert hasattr(exa.beta.agent, "runs")
    assert not hasattr(exa.beta.agent, "run")
    assert not hasattr(exa, "agent")


def test_exa_exposes_responses_namespace():
    exa = Exa(api_key="test-api-key")
    assert hasattr(exa, "responses")


def test_responses_create_uses_agent_model_and_reasoning_effort(mock_client):
    mock_client.request.return_value = _make_response()
    responses = Exa(api_key="test-api-key").responses
    responses._client = mock_client

    result = responses.create(
        input="Find recent funding rounds.",
        reasoning={"effort": "minimal"},
        temperature=0,
        tools=[{"type": "function", "name": "ignored_tool"}],
    )

    assert result.id == "resp_agent_run_123"
    assert result.output_text == "Returned 1 company."
    mock_client.request.assert_called_once_with(
        "/responses",
        data={
            "input": "Find recent funding rounds.",
            "model": "agent",
            "reasoning": {"effort": "minimal"},
            "temperature": 0,
            "tools": [{"type": "function", "name": "ignored_tool"}],
        },
        method="POST",
    )


def test_responses_create_rejects_streaming(mock_client):
    responses = Exa(api_key="test-api-key").responses
    responses._client = mock_client

    with pytest.raises(ValueError, match="Streaming Responses"):
        responses.create(input="Find recent funding rounds.", stream=True)

    mock_client.request.assert_not_called()


def test_create_agent_run(run_client, mock_client):
    mock_client.request.return_value = _make_run()

    result = run_client.create(
        betas=AGENT_BETAS,
        query="Find recent funding rounds.",
        system_prompt="Prefer primary sources.",
        input={"data": [{"company": "Example AI"}]},
        output_schema={"type": "object"},
        effort="high",
        metadata={"workflow": "funding-watch"},
    )

    assert result.id == "agent_run_123"
    assert result.output.structured == {"companies": [{"name": "Example AI"}]}
    assert result.usage.agent_compute_units == 0.1
    mock_client.request.assert_called_once_with(
        "/agent/runs",
        data={
            "query": "Find recent funding rounds.",
            "systemPrompt": "Prefer primary sources.",
            "input": {"data": [{"company": "Example AI"}]},
            "outputSchema": {"type": "object"},
            "effort": "high",
            "metadata": {"workflow": "funding-watch"},
        },
        method="POST",
        params=None,
        headers={"Exa-Beta": AGENT_BETA_HEADER},
    )


def test_create_agent_run_requires_explicit_betas(run_client):
    with pytest.raises(ValueError, match="betas"):
        run_client.create(betas=[], query="Find recent funding rounds.")


def test_create_agent_run_converts_pydantic_output_schema(run_client, mock_client):
    mock_client.request.return_value = _make_run()

    run_client.create(
        betas=AGENT_BETAS,
        query="Find recent funding rounds.",
        output_schema=_CompanyOutput,
    )

    payload = mock_client.request.call_args.kwargs["data"]
    assert payload["outputSchema"]["type"] == "object"
    assert "company_name" in payload["outputSchema"]["properties"]


def test_create_agent_run_accepts_contact_fields_in_output_schema(run_client, mock_client):
    mock_client.request.return_value = _make_run()

    run_client.create(
        betas=AGENT_BETAS,
        query="Find people at AI infrastructure companies and return work emails when available.",
        output_schema={
            "type": "object",
            "properties": {
                "people": {
                    "type": "array",
                    "maxItems": 10,
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "contact_email": {"type": "string", "format": "email"},
                            "linkedin_url": {"type": "string", "format": "uri"},
                        },
                    },
                },
            },
        },
    )

    payload = mock_client.request.call_args.kwargs["data"]
    assert payload["outputSchema"]["properties"]["people"]["maxItems"] == 10
    assert (
        payload["outputSchema"]["properties"]["people"]["items"]["properties"][
            "contact_email"
        ]["format"]
        == "email"
    )
    assert "enrichments" not in payload


def test_get_cancel_and_delete_agent_run_paths(run_client, mock_client):
    mock_client.request.side_effect = [
        _make_run(),
        {**_make_run(), "status": "cancelled", "stopReason": "cancelled"},
        {"id": "agent_run_123", "object": "agent_run.deleted", "deleted": True},
    ]

    assert run_client.get("agent_run_123", betas=AGENT_BETAS).id == "agent_run_123"
    assert run_client.cancel("agent_run_123", betas=AGENT_BETAS).status == "cancelled"
    assert run_client.delete("agent_run_123", betas=AGENT_BETAS).deleted is True

    assert mock_client.request.call_args_list[0].args == ("/agent/runs/agent_run_123",)
    assert mock_client.request.call_args_list[0].kwargs["method"] == "GET"
    assert mock_client.request.call_args_list[1].args == (
        "/agent/runs/agent_run_123/cancel",
    )
    assert mock_client.request.call_args_list[1].kwargs["method"] == "POST"
    assert mock_client.request.call_args_list[2].args == ("/agent/runs/agent_run_123",)
    assert mock_client.request.call_args_list[2].kwargs["method"] == "DELETE"


def test_list_agent_runs(run_client, mock_client):
    mock_client.request.return_value = {
        "object": "list",
        "data": [_make_run("agent_run_1")],
        "hasMore": False,
        "nextCursor": None,
    }

    result = run_client.list(betas=AGENT_BETAS, limit=10)

    assert isinstance(result, ListAgentRunsResponse)
    assert result.data[0].id == "agent_run_1"
    mock_client.request.assert_called_once_with(
        "/agent/runs",
        data=None,
        method="GET",
        params={"limit": "10"},
        headers={"Exa-Beta": AGENT_BETA_HEADER},
    )


def test_list_all_and_get_all_agent_runs(run_client, mock_client):
    mock_client.request.side_effect = [
        {
            "object": "list",
            "data": [_make_run("agent_run_1")],
            "hasMore": True,
            "nextCursor": "cursor_2",
        },
        {
            "object": "list",
            "data": [_make_run("agent_run_2")],
            "hasMore": False,
            "nextCursor": None,
        },
        {
            "object": "list",
            "data": [_make_run("agent_run_3")],
            "hasMore": False,
            "nextCursor": None,
        },
    ]

    assert [run.id for run in run_client.list_all(betas=AGENT_BETAS, limit=1)] == [
        "agent_run_1",
        "agent_run_2",
    ]
    assert [run.id for run in run_client.get_all(betas=AGENT_BETAS, limit=1)] == [
        "agent_run_3"
    ]
    assert mock_client.request.call_args_list[0].kwargs["params"] == {"limit": "1"}
    assert mock_client.request.call_args_list[1].kwargs["params"] == {
        "cursor": "cursor_2",
        "limit": "1",
    }


def test_agent_run_events(run_client, mock_client):
    mock_client.request.return_value = {
        "object": "list",
        "data": [
            {
                "id": "1",
                "event": "agent_run.created",
                "data": {"id": "agent_run_123", "status": "queued"},
                "createdAt": "2026-05-07T18:31:00.000Z",
            }
        ],
        "hasMore": False,
        "nextCursor": None,
    }

    result = run_client.events.list("agent_run_123", betas=AGENT_BETAS, limit=20)

    assert result.data[0].event == "agent_run.created"
    mock_client.request.assert_called_once_with(
        "/agent/runs/agent_run_123/events",
        data=None,
        method="GET",
        params={"limit": "20"},
        headers={"Exa-Beta": AGENT_BETA_HEADER},
    )


def test_cancel_and_delete_agent_run(run_client, mock_client):
    mock_client.request.side_effect = [
        {**_make_run(), "status": "cancelled", "stopReason": "cancelled"},
        {"id": "agent_run_123", "object": "agent_run.deleted", "deleted": True},
    ]

    cancelled = run_client.cancel("agent_run_123", betas=AGENT_BETAS)
    deleted = run_client.delete("agent_run_123", betas=AGENT_BETAS)

    assert cancelled.status == "cancelled"
    assert deleted.deleted is True
    assert mock_client.request.call_args_list[0].kwargs["headers"] == {
        "Exa-Beta": AGENT_BETA_HEADER
    }
    assert mock_client.request.call_args_list[1].kwargs["headers"] == {
        "Exa-Beta": AGENT_BETA_HEADER
    }


def test_stream_create_sets_sse_headers(run_client, mock_client):
    response = MagicMock()
    response.iter_lines.return_value = []
    mock_client.request.return_value = response

    events = run_client.create(
        betas=AGENT_BETAS, query="Find companies.", stream=True
    )

    assert list(events) == []
    mock_client.request.assert_called_once_with(
        "/agent/runs",
        data={"query": "Find companies."},
        method="POST",
        params=None,
        headers={"Exa-Beta": AGENT_BETA_HEADER, "Accept": "text/event-stream"},
    )
    response.close.assert_called_once()


def test_sync_streaming_request_raises_and_closes_error_response(monkeypatch):
    exa = Exa(api_key="test-api-key")
    response = MagicMock(status_code=400, text="beta header missing")
    post = MagicMock(return_value=response)
    monkeypatch.setattr("exa_py.api.requests.post", post)

    with pytest.raises(ValueError, match="beta header missing"):
        exa.request(
            "/agent/runs",
            data={"query": "Find companies."},
            headers={"Accept": "text/event-stream"},
        )

    response.close.assert_called_once()


def test_poll_until_finished_returns_terminal_run(run_client, mock_client, monkeypatch):
    mock_client.request.side_effect = [
        {**_make_run(), "status": "running"},
        {**_make_run(), "status": "completed"},
    ]
    sleep = MagicMock()
    monkeypatch.setattr("exa_py.agent.client.time.sleep", sleep)

    result = run_client.poll_until_finished(
        "agent_run_123", betas=AGENT_BETAS, poll_interval=5, timeout_ms=1000
    )

    assert result.status == "completed"
    sleep.assert_called_once_with(0.005)


def test_poll_until_finished_times_out(run_client, mock_client, monkeypatch):
    mock_client.request.return_value = {**_make_run(), "status": "running"}
    times = iter([0.0, 2.0])
    monkeypatch.setattr("exa_py.agent.client.time.monotonic", lambda: next(times))
    monkeypatch.setattr("exa_py.agent.client.time.sleep", MagicMock())

    with pytest.raises(TimeoutError):
        run_client.poll_until_finished(
            "agent_run_123", betas=AGENT_BETAS, poll_interval=5, timeout_ms=1
        )


@pytest.mark.asyncio
async def test_async_agent_create():
    client = MagicMock()
    client.async_request = AsyncMock(return_value=_make_run())
    run = AsyncBetaClient(client).agent.runs

    result = await run.create(
        betas=AGENT_BETAS, query="Find recent funding rounds.", effort="auto"
    )

    assert result.id == "agent_run_123"
    client.async_request.assert_awaited_once_with(
        "/agent/runs",
        data={"query": "Find recent funding rounds.", "effort": "auto"},
        method="POST",
        params=None,
        headers={"Exa-Beta": AGENT_BETA_HEADER},
    )


@pytest.mark.asyncio
async def test_async_responses_create():
    client = MagicMock()
    client.async_request = AsyncMock(return_value=_make_response())
    responses = AsyncExa(api_key="test-api-key").responses
    responses._client = client

    result = await responses.create(
        input="Find recent funding rounds.",
        reasoning={"effort": "high"},
    )

    assert result.output_text == "Returned 1 company."
    client.async_request.assert_awaited_once_with(
        "/responses",
        data={
            "input": "Find recent funding rounds.",
            "model": "agent",
            "reasoning": {"effort": "high"},
        },
        method="POST",
    )


@pytest.mark.asyncio
async def test_async_create_stream_parses_sse():
    client = MagicMock()
    client.async_request = AsyncMock(
        return_value=_MockAsyncSseResponse(
            [
                "id: 1",
                "event: agent_run.created",
                'data: {"id":"agent_run_123","status":"queued"}',
                "",
            ]
        )
    )
    run = AsyncBetaClient(client).agent.runs

    stream = await run.create(betas=AGENT_BETAS, query="Find companies.", stream=True)
    events = [event async for event in stream]

    assert events[0].event == "agent_run.created"
    assert events[0].data == {"id": "agent_run_123", "status": "queued"}
    assert client.async_request.return_value.closed is True
    client.async_request.assert_awaited_once_with(
        "/agent/runs",
        data={"query": "Find companies."},
        method="POST",
        params=None,
        headers={"Exa-Beta": AGENT_BETA_HEADER, "Accept": "text/event-stream"},
    )


@pytest.mark.asyncio
async def test_async_streaming_request_raises_and_closes_error_response():
    exa = AsyncExa(api_key="test-api-key")
    response = httpx.Response(
        400,
        content=b"beta header missing",
        request=httpx.Request("POST", "https://api.exa.ai/agent/runs"),
    )
    client = MagicMock()
    client.send = AsyncMock(return_value=response)
    exa._client = client

    with pytest.raises(ValueError, match="beta header missing"):
        await exa.async_request(
            "/agent/runs",
            data={"query": "Find companies."},
            headers={"Accept": "text/event-stream"},
        )

    assert response.is_closed


@pytest.mark.asyncio
async def test_async_list_all_and_get_all_agent_runs():
    client = MagicMock()
    client.async_request = AsyncMock(
        side_effect=[
            {
                "object": "list",
                "data": [_make_run("agent_run_1")],
                "hasMore": True,
                "nextCursor": "cursor_2",
            },
            {
                "object": "list",
                "data": [_make_run("agent_run_2")],
                "hasMore": False,
                "nextCursor": None,
            },
            {
                "object": "list",
                "data": [_make_run("agent_run_3")],
                "hasMore": False,
                "nextCursor": None,
            },
        ]
    )
    run = AsyncBetaClient(client).agent.runs

    assert [item.id async for item in run.list_all(betas=AGENT_BETAS, limit=1)] == [
        "agent_run_1",
        "agent_run_2",
    ]
    assert [item.id for item in await run.get_all(betas=AGENT_BETAS, limit=1)] == [
        "agent_run_3"
    ]


@pytest.mark.asyncio
async def test_async_poll_until_finished_returns_terminal_run(monkeypatch):
    client = MagicMock()
    client.async_request = AsyncMock(
        side_effect=[
            {**_make_run(), "status": "running"},
            {**_make_run(), "status": "completed"},
        ]
    )
    sleep = AsyncMock()
    monkeypatch.setattr("exa_py.agent.async_client.asyncio.sleep", sleep)
    run = AsyncBetaClient(client).agent.runs

    result = await run.poll_until_finished(
        "agent_run_123", betas=AGENT_BETAS, poll_interval=5, timeout_ms=1000
    )

    assert result.status == "completed"
    sleep.assert_awaited_once_with(0.005)
