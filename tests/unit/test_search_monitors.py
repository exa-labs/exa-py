import pytest
from unittest.mock import AsyncMock, MagicMock

from exa_py.monitors.client import SearchMonitorsClient, SearchMonitorRunsClient
from exa_py.monitors.types import (
    ListSearchMonitorsResponse,
    SearchMonitor,
    SearchMonitorSearch,
    SearchMonitorWebhook,
)


@pytest.fixture
def mock_client():
    return MagicMock()


@pytest.fixture
def monitors_client(mock_client):
    return SearchMonitorsClient(mock_client)


def _make_monitor(id: str) -> dict:
    return {
        "id": id,
        "name": f"Monitor {id}",
        "status": "active",
        "search": {"query": "test"},
        "trigger": {"type": "interval", "period": "1d"},
        "outputSchema": None,
        "metadata": None,
        "webhook": {"url": "https://example.com/hook"},
        "nextRunAt": None,
        "createdAt": "2026-01-01T00:00:00Z",
        "updatedAt": "2026-01-01T00:00:00Z",
    }


class TestSearchMonitorsListAll:
    def test_list_all_single_page(self, monitors_client, mock_client):
        mock_client.request.return_value = {
            "data": [_make_monitor("sm_1"), _make_monitor("sm_2")],
            "hasMore": False,
            "nextCursor": None,
        }
        results = list(monitors_client.list_all())
        assert len(results) == 2
        assert results[0].id == "sm_1"
        assert results[1].id == "sm_2"

    def test_list_all_multiple_pages(self, monitors_client, mock_client):
        mock_client.request.side_effect = [
            {"data": [_make_monitor("sm_1")], "hasMore": True, "nextCursor": "cursor_1"},
            {"data": [_make_monitor("sm_2")], "hasMore": False, "nextCursor": None},
        ]
        results = list(monitors_client.list_all())
        assert len(results) == 2
        assert results[0].id == "sm_1"
        assert results[1].id == "sm_2"
        assert mock_client.request.call_count == 2

    def test_list_all_empty(self, monitors_client, mock_client):
        mock_client.request.return_value = {"data": [], "hasMore": False, "nextCursor": None}
        results = list(monitors_client.list_all())
        assert results == []

    def test_list_all_passes_status_filter(self, monitors_client, mock_client):
        mock_client.request.return_value = {
            "data": [_make_monitor("sm_1")],
            "hasMore": False,
            "nextCursor": None,
        }
        list(monitors_client.list_all(status="active"))
        call_args = mock_client.request.call_args
        assert "active" in str(call_args)

    def test_get_all_returns_list(self, monitors_client, mock_client):
        mock_client.request.return_value = {
            "data": [_make_monitor("sm_1"), _make_monitor("sm_2")],
            "hasMore": False,
            "nextCursor": None,
        }
        results = monitors_client.get_all()
        assert isinstance(results, list)
        assert len(results) == 2


import asyncio
from exa_py.monitors.async_client import AsyncSearchMonitorsClient


@pytest.fixture
def async_mock_client():
    client = MagicMock()
    client.async_request = AsyncMock()
    return client


@pytest.fixture
def async_monitors_client(async_mock_client):
    return AsyncSearchMonitorsClient(async_mock_client)


class TestAsyncSearchMonitorsListAll:
    def test_list_all_single_page(self, async_monitors_client, async_mock_client):
        async def _run():
            async_mock_client.async_request.return_value = {
                "data": [_make_monitor("sm_1"), _make_monitor("sm_2")],
                "hasMore": False,
                "nextCursor": None,
            }
            results = []
            async for monitor in async_monitors_client.list_all():
                results.append(monitor)
            return results
        results = asyncio.run(_run())
        assert len(results) == 2
        assert results[0].id == "sm_1"

    def test_list_all_multiple_pages(self, async_monitors_client, async_mock_client):
        async def _run():
            async_mock_client.async_request.side_effect = [
                {"data": [_make_monitor("sm_1")], "hasMore": True, "nextCursor": "cursor_1"},
                {"data": [_make_monitor("sm_2")], "hasMore": False, "nextCursor": None},
            ]
            results = []
            async for monitor in async_monitors_client.list_all():
                results.append(monitor)
            return results
        results = asyncio.run(_run())
        assert len(results) == 2
        assert async_mock_client.async_request.call_count == 2

    def test_get_all_returns_list(self, async_monitors_client, async_mock_client):
        async def _run():
            async_mock_client.async_request.return_value = {
                "data": [_make_monitor("sm_1")],
                "hasMore": False,
                "nextCursor": None,
            }
            return await async_monitors_client.get_all()
        results = asyncio.run(_run())
        assert isinstance(results, list)
        assert len(results) == 1


def _make_run(id: str) -> dict:
    return {
        "id": id,
        "monitorId": "sm_123",
        "status": "completed",
        "output": None,
        "failReason": None,
        "startedAt": "2026-01-01T00:00:00Z",
        "completedAt": "2026-01-01T00:05:00Z",
        "failedAt": None,
        "cancelledAt": None,
        "durationMs": 300000,
        "createdAt": "2026-01-01T00:00:00Z",
        "updatedAt": "2026-01-01T00:05:00Z",
    }


class TestSearchMonitorRunsListAll:
    def test_list_all_single_page(self, monitors_client, mock_client):
        mock_client.request.return_value = {
            "data": [_make_run("run_1"), _make_run("run_2")],
            "hasMore": False,
            "nextCursor": None,
        }
        results = list(monitors_client.runs.list_all("sm_123"))
        assert len(results) == 2
        assert results[0].id == "run_1"

    def test_list_all_multiple_pages(self, monitors_client, mock_client):
        mock_client.request.side_effect = [
            {"data": [_make_run("run_1")], "hasMore": True, "nextCursor": "cursor_1"},
            {"data": [_make_run("run_2")], "hasMore": False, "nextCursor": None},
        ]
        results = list(monitors_client.runs.list_all("sm_123"))
        assert len(results) == 2
        assert mock_client.request.call_count == 2

    def test_get_all_returns_list(self, monitors_client, mock_client):
        mock_client.request.return_value = {
            "data": [_make_run("run_1")],
            "hasMore": False,
            "nextCursor": None,
        }
        results = monitors_client.runs.get_all("sm_123")
        assert isinstance(results, list)
        assert len(results) == 1


from exa_py.monitors.types import TriggerSearchMonitorResponse


class TestTriggerResponse:
    def test_trigger_returns_typed_response(self, monitors_client, mock_client):
        mock_client.request.return_value = {"triggered": True}
        result = monitors_client.trigger("sm_123")
        assert isinstance(result, TriggerSearchMonitorResponse)
        assert result.triggered is True


class TestSearchMonitorRunOutputContent:
    """Runs configured with an outputSchema return ``output.content`` as a
    structured object, so the field must accept both ``str`` and ``dict``."""

    def _make_run_with_content(self, content) -> dict:
        run = _make_run("run_1")
        run["output"] = {"results": None, "content": content, "grounding": None}
        return run

    def test_get_run_with_structured_content(self, monitors_client, mock_client):
        structured = {"summary": "AI breakthroughs", "count": 3}
        mock_client.request.return_value = self._make_run_with_content(structured)
        run = monitors_client.runs.get("sm_123", "run_1")
        assert run.output is not None
        assert run.output.content == structured

    def test_get_run_with_string_content(self, monitors_client, mock_client):
        mock_client.request.return_value = self._make_run_with_content("plain text")
        run = monitors_client.runs.get("sm_123", "run_1")
        assert run.output is not None
        assert run.output.content == "plain text"

    def test_list_runs_with_structured_content(self, monitors_client, mock_client):
        structured = {"summary": "AI breakthroughs"}
        mock_client.request.return_value = {
            "data": [self._make_run_with_content(structured)],
            "hasMore": False,
            "nextCursor": None,
        }
        runs = monitors_client.runs.list("sm_123")
        assert runs.data[0].output.content == structured
