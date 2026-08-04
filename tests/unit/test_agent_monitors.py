from unittest.mock import AsyncMock, MagicMock

import pytest

from exa_py import AsyncExa, Exa
from exa_py.agent import (
    AgentMonitor,
    AgentMonitorChangesClient,
    AgentMonitorEntitiesClient,
    AgentMonitorSnapshotFailedError,
    AgentMonitorSnapshotsClient,
    AgentMonitorsClient,
    AgentNamespace,
    AsyncAgentMonitorsClient,
    AsyncAgentNamespace,
    DeletedAgentMonitor,
    ListAgentMonitorChangesResponse,
    ListAgentMonitorEntitiesResponse,
    ListAgentMonitorsResponse,
)


@pytest.fixture
def mock_client():
    return MagicMock()


@pytest.fixture
def monitors_client(mock_client):
    return AgentNamespace(mock_client).monitors


def _make_monitor(monitor_id: str = "agentmon_123", status: str = "active") -> dict:
    return {
        "id": monitor_id,
        "object": "agent_monitor",
        "status": status,
        "cadence": "7d",
        "fields": [
            {
                "id": "agentfield_1",
                "name": "ceo",
                "description": "The company's current CEO",
                "type": "static",
            },
            {
                "id": "agentfield_2",
                "name": "funding",
                "description": "New funding rounds",
                "type": "dynamic",
            },
        ],
        "entityCount": 2,
        "version": 3,
        "createdAt": "2026-01-01T00:00:00.000Z",
        "lastRefreshAt": "2026-01-08T00:00:00.000Z",
        "refresh": {"state": "idle"},
        "creation": {"state": "idle"},
        "usage": {"totalAcus": 12, "lastRefreshAcus": 4},
    }


def _make_entity_view() -> dict:
    return {
        "entity": {
            "id": "agententity_1",
            "name": "Acme Corp",
            "domain": "acme.com",
        },
        "contents": {
            "agentfield_1": {
                "value": "Jane Doe",
                "sourceUrls": ["https://acme.com/about"],
                "updatedAt": "2026-01-08T00:00:00.000Z",
            }
        },
    }


def _make_change() -> dict:
    return {
        "type": "content.upserted",
        "entity": {"id": "agententity_1", "name": "Acme Corp"},
        "field": {"id": "agentfield_2", "name": "funding"},
        "content": {
            "value": "Raised a $30M Series B",
            "sourceUrls": ["https://news.example.com/acme-series-b"],
            "updatedAt": "2026-01-08T00:00:00.000Z",
        },
        "version": 3,
        "createdAt": "2026-01-08T00:00:01.000Z",
    }


def _make_snapshot(status: str = "running", **extra) -> dict:
    snapshot = {
        "id": "agentsnap_123",
        "object": "agent_monitor.snapshot",
        "status": status,
        "startTime": "2026-01-01T00:00:00.000Z",
        "endTime": "2026-01-08T00:00:00.000Z",
        "createdAt": "2026-01-09T00:00:00.000Z",
        "expiresAt": "2026-01-10T00:00:00.000Z",
    }
    snapshot.update(extra)
    return snapshot


_SNAPSHOT_KWARGS = {
    "entities": [{"name": "Acme Corp", "domain": "acme.com"}],
    "fields": [
        {"name": "funding", "description": "New funding rounds", "type": "dynamic"}
    ],
    "start_date": "2026-01-01",
    "end_date": "2026-01-08",
}


def test_exa_exposes_monitors_under_agent_namespace():
    exa = Exa(api_key="test-api-key")
    assert isinstance(exa.agent.monitors, AgentMonitorsClient)
    assert isinstance(exa.agent.monitors.entities, AgentMonitorEntitiesClient)
    assert isinstance(exa.agent.monitors.changes, AgentMonitorChangesClient)
    assert isinstance(exa.agent.monitors.snapshots, AgentMonitorSnapshotsClient)


def test_async_exa_exposes_monitors_under_agent_namespace():
    exa = AsyncExa(api_key="test-api-key")
    assert isinstance(exa.agent.monitors, AsyncAgentMonitorsClient)


def test_create_monitor(monitors_client, mock_client):
    mock_client.request.return_value = _make_monitor(status="creating")

    result = monitors_client.create(
        cadence="7d",
        entities=[
            {"name": "Acme Corp", "domain": "acme.com"},
            {
                "name": "Globex",
                "domain": "globex.com",
                "description": "Industrial conglomerate",
            },
        ],
        fields=[
            {"name": "ceo", "description": "The company's current CEO"},
            {"name": "funding", "description": "New funding rounds", "type": "dynamic"},
        ],
    )

    assert isinstance(result, AgentMonitor)
    assert result.status == "creating"
    mock_client.request.assert_called_once_with(
        "/agent/monitors",
        data={
            "cadence": "7d",
            "entities": [
                {"name": "Acme Corp", "domain": "acme.com"},
                {
                    "name": "Globex",
                    "domain": "globex.com",
                    "description": "Industrial conglomerate",
                },
            ],
            "fields": [
                {"name": "ceo", "description": "The company's current CEO"},
                {
                    "name": "funding",
                    "description": "New funding rounds",
                    "type": "dynamic",
                },
            ],
        },
        method="POST",
        params=None,
        headers={},
    )


def test_create_monitor_sends_idempotency_key(monitors_client, mock_client):
    mock_client.request.return_value = _make_monitor(status="creating")

    monitors_client.create(
        cadence="12h",
        entities=[{"name": "Acme Corp", "domain": "acme.com"}],
        fields=[{"name": "ceo", "description": "The company's current CEO"}],
        idempotency_key="my-key-1",
    )

    assert mock_client.request.call_args.kwargs["headers"] == {
        "Idempotency-Key": "my-key-1"
    }


def test_get_monitor(monitors_client, mock_client):
    mock_client.request.return_value = _make_monitor()

    result = monitors_client.get("agentmon_123")

    assert isinstance(result, AgentMonitor)
    assert result.entity_count == 2
    assert result.usage is not None and result.usage.total_acus == 12
    mock_client.request.assert_called_once_with(
        "/agent/monitors/agentmon_123",
        data=None,
        method="GET",
        params=None,
        headers={},
    )


def test_list_monitors(monitors_client, mock_client):
    mock_client.request.return_value = {
        "object": "list",
        "data": [_make_monitor("agentmon_1")],
        "hasMore": False,
        "nextCursor": None,
    }

    result = monitors_client.list(limit=10)

    assert isinstance(result, ListAgentMonitorsResponse)
    assert result.data[0].id == "agentmon_1"
    mock_client.request.assert_called_once_with(
        "/agent/monitors",
        data=None,
        method="GET",
        params={"limit": "10"},
        headers={},
    )


def test_list_all_and_get_all_monitors(monitors_client, mock_client):
    mock_client.request.side_effect = [
        {
            "object": "list",
            "data": [_make_monitor("agentmon_1")],
            "hasMore": True,
            "nextCursor": "agentmon_1",
        },
        {
            "object": "list",
            "data": [_make_monitor("agentmon_2")],
            "hasMore": False,
            "nextCursor": None,
        },
    ]

    monitors = monitors_client.get_all()

    assert [monitor.id for monitor in monitors] == ["agentmon_1", "agentmon_2"]
    assert mock_client.request.call_count == 2
    second_call = mock_client.request.call_args_list[1]
    assert second_call.kwargs["params"] == {"cursor": "agentmon_1"}


def test_delete_monitor(monitors_client, mock_client):
    mock_client.request.return_value = {
        "id": "agentmon_123",
        "object": "agent_monitor.deleted",
        "deleted": True,
    }

    result = monitors_client.delete("agentmon_123")

    assert isinstance(result, DeletedAgentMonitor)
    assert result.deleted is True
    mock_client.request.assert_called_once_with(
        "/agent/monitors/agentmon_123",
        data=None,
        method="DELETE",
        params=None,
        headers={},
    )


def test_add_entities(monitors_client, mock_client):
    mock_client.request.return_value = _make_monitor()

    result = monitors_client.entities.add(
        "agentmon_123",
        entities=[{"name": "Initech", "domain": "initech.com"}],
    )

    assert isinstance(result, AgentMonitor)
    mock_client.request.assert_called_once_with(
        "/agent/monitors/agentmon_123/entities",
        data={"entities": [{"name": "Initech", "domain": "initech.com"}]},
        method="POST",
        params=None,
        headers={},
    )


def test_list_entities_with_since(monitors_client, mock_client):
    mock_client.request.return_value = {
        "object": "list",
        "data": [_make_entity_view()],
        "hasMore": False,
        "nextCursor": None,
        "version": 3,
    }

    result = monitors_client.entities.list(
        "agentmon_123",
        cursor="abc",
        limit=50,
        since="2026-01-07T00:00:00Z",
    )

    assert isinstance(result, ListAgentMonitorEntitiesResponse)
    assert result.data[0].entity.name == "Acme Corp"
    assert result.data[0].contents["agentfield_1"].value == "Jane Doe"
    mock_client.request.assert_called_once_with(
        "/agent/monitors/agentmon_123/entities",
        data=None,
        method="GET",
        params={"cursor": "abc", "limit": "50", "since": "2026-01-07T00:00:00Z"},
        headers={},
    )


def test_list_all_entities_paginates(monitors_client, mock_client):
    mock_client.request.side_effect = [
        {
            "object": "list",
            "data": [_make_entity_view()],
            "hasMore": True,
            "nextCursor": "cursor-2",
            "version": 3,
        },
        {
            "object": "list",
            "data": [_make_entity_view()],
            "hasMore": False,
            "nextCursor": None,
            "version": 3,
        },
    ]

    entities = monitors_client.entities.get_all("agentmon_123")

    assert len(entities) == 2
    assert mock_client.request.call_count == 2
    second_call = mock_client.request.call_args_list[1]
    assert second_call.kwargs["params"] == {"cursor": "cursor-2"}


def test_list_changes(monitors_client, mock_client):
    mock_client.request.return_value = {
        "object": "list",
        "data": [_make_change()],
        "hasMore": False,
        "nextCursor": "change-cursor-1",
        "version": 3,
    }

    result = monitors_client.changes.list(
        "agentmon_123", since="2026-01-07T00:00:00Z"
    )

    assert isinstance(result, ListAgentMonitorChangesResponse)
    assert result.data[0].created_at == "2026-01-08T00:00:01.000Z"
    assert result.data[0].content.value == "Raised a $30M Series B"
    mock_client.request.assert_called_once_with(
        "/agent/monitors/agentmon_123/changes",
        data=None,
        method="GET",
        params={"since": "2026-01-07T00:00:00Z"},
        headers={},
    )


def test_list_all_changes_resumes_from_cursor(monitors_client, mock_client):
    mock_client.request.side_effect = [
        {
            "object": "list",
            "data": [_make_change()],
            "hasMore": True,
            "nextCursor": "change-cursor-2",
            "version": 3,
        },
        {
            "object": "list",
            "data": [_make_change()],
            "hasMore": False,
            "nextCursor": "change-cursor-3",
            "version": 3,
        },
    ]

    changes = monitors_client.changes.get_all(
        "agentmon_123", cursor="change-cursor-1"
    )

    assert len(changes) == 2
    first_call, second_call = mock_client.request.call_args_list
    assert first_call.kwargs["params"] == {"cursor": "change-cursor-1"}
    assert second_call.kwargs["params"] == {"cursor": "change-cursor-2"}


def test_create_snapshot(monitors_client, mock_client):
    mock_client.request.return_value = _make_snapshot()

    result = monitors_client.snapshots.create(**_SNAPSHOT_KWARGS, end_hour=12)

    assert result.status == "running"
    mock_client.request.assert_called_once_with(
        "/agent/monitors/snapshot",
        data={
            "entities": [{"name": "Acme Corp", "domain": "acme.com"}],
            "fields": [
                {
                    "name": "funding",
                    "description": "New funding rounds",
                    "type": "dynamic",
                }
            ],
            "startDate": "2026-01-01",
            "endDate": "2026-01-08",
            "endHour": 12,
        },
        method="POST",
        params=None,
        headers={},
    )


def test_get_snapshot(monitors_client, mock_client):
    mock_client.request.return_value = _make_snapshot(
        status="completed",
        data=[
            {
                "name": "Acme Corp",
                "fields": {"funding": "Raised a $30M Series B"},
                "sourceUrls": ["https://news.example.com/acme-series-b"],
            }
        ],
        warnings=[],
    )

    result = monitors_client.snapshots.get("agentsnap_123")

    assert result.status == "completed"
    assert result.data is not None
    assert result.data[0].fields["funding"] == "Raised a $30M Series B"
    mock_client.request.assert_called_once_with(
        "/agent/monitors/snapshot/agentsnap_123",
        data=None,
        method="GET",
        params=None,
        headers={},
    )


def test_create_and_wait_snapshot(monitors_client, mock_client):
    mock_client.request.side_effect = [
        _make_snapshot(),
        _make_snapshot(),
        _make_snapshot(status="completed", data=[]),
    ]

    result = monitors_client.snapshots.create_and_wait(
        **_SNAPSHOT_KWARGS, poll_interval=1
    )

    assert result.status == "completed"
    assert mock_client.request.call_count == 3


def test_create_and_wait_snapshot_raises_on_failure(monitors_client, mock_client):
    mock_client.request.side_effect = [
        _make_snapshot(),
        _make_snapshot(status="failed", error="newsfeed unavailable"),
    ]

    with pytest.raises(AgentMonitorSnapshotFailedError) as excinfo:
        monitors_client.snapshots.create_and_wait(**_SNAPSHOT_KWARGS, poll_interval=1)

    assert excinfo.value.snapshot.error == "newsfeed unavailable"


def test_poll_until_finished_times_out(monitors_client, mock_client):
    mock_client.request.return_value = _make_snapshot()

    with pytest.raises(TimeoutError):
        monitors_client.snapshots.poll_until_finished(
            "agentsnap_123", poll_interval=1, timeout_ms=5
        )


@pytest.mark.asyncio
async def test_async_create_monitor():
    client = MagicMock()
    client.async_request = AsyncMock(return_value=_make_monitor(status="creating"))
    monitors = AsyncAgentNamespace(client).monitors

    result = await monitors.create(
        cadence="7d",
        entities=[{"name": "Acme Corp", "domain": "acme.com"}],
        fields=[{"name": "ceo", "description": "The company's current CEO"}],
    )

    assert result.status == "creating"
    client.async_request.assert_awaited_once_with(
        "/agent/monitors",
        data={
            "cadence": "7d",
            "entities": [{"name": "Acme Corp", "domain": "acme.com"}],
            "fields": [{"name": "ceo", "description": "The company's current CEO"}],
        },
        method="POST",
        params=None,
        headers={},
    )


@pytest.mark.asyncio
async def test_async_list_all_entities_paginates():
    client = MagicMock()
    client.async_request = AsyncMock(
        side_effect=[
            {
                "object": "list",
                "data": [_make_entity_view()],
                "hasMore": True,
                "nextCursor": "cursor-2",
                "version": 3,
            },
            {
                "object": "list",
                "data": [_make_entity_view()],
                "hasMore": False,
                "nextCursor": None,
                "version": 3,
            },
        ]
    )
    monitors = AsyncAgentNamespace(client).monitors

    entities = await monitors.entities.get_all("agentmon_123")

    assert len(entities) == 2
    assert client.async_request.await_count == 2


@pytest.mark.asyncio
async def test_async_create_and_wait_snapshot():
    client = MagicMock()
    client.async_request = AsyncMock(
        side_effect=[
            _make_snapshot(),
            _make_snapshot(status="completed", data=[]),
        ]
    )
    monitors = AsyncAgentNamespace(client).monitors

    result = await monitors.snapshots.create_and_wait(
        **_SNAPSHOT_KWARGS, poll_interval=1
    )

    assert result.status == "completed"
