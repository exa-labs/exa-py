"""list_all / get_all on the Websets monitors, imports and events clients.

Each helper follows the listing's cursor until ``hasMore`` is false, forwards its
filters to every page, and drops a starting cursor given in ``extra_query`` after
the first page.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from exa_py.websets.events.client import AsyncEventsClient, EventsClient
from exa_py.websets.imports.client import AsyncImportsClient, ImportsClient
from exa_py.websets.monitors.client import AsyncMonitorsClient, MonitorsClient
from exa_py.websets.types import EventType


def _monitor(id: str) -> dict:
    return {
        "id": id,
        "object": "monitor",
        "status": "enabled",
        "websetId": "ws_123",
        "cadence": {"cron": "0 9 * * *", "timezone": "Etc/UTC"},
        "behavior": {
            "type": "search",
            "config": {
                "query": "AI startups",
                "criteria": [{"description": "Must be AI focused"}],
                "entity": {"type": "company"},
                "count": 10,
                "behavior": "append",
            },
        },
        "metadata": {},
        "createdAt": "2023-01-01T00:00:00Z",
        "updatedAt": "2023-01-01T00:00:00Z",
    }


def _import(id: str) -> dict:
    return {
        "id": id,
        "object": "import",
        "title": "Sample Company Data",
        "format": "csv",
        "entity": {"type": "company"},
        "size": 1024.0,
        "count": 100.0,
        "status": "completed",
        "csv": {"identifier": 1},
        "metadata": {},
        "createdAt": "2023-01-01T00:00:00Z",
        "updatedAt": "2023-01-01T00:05:00Z",
        "completedAt": "2023-01-01T00:05:00Z",
        "failedAt": None,
        "failedReason": None,
        "failedMessage": None,
    }


def _event(id: str) -> dict:
    return {
        "id": id,
        "object": "event",
        "type": "webset.created",
        "createdAt": "2023-01-01T00:00:00Z",
        "data": {
            "id": "ws_123",
            "object": "webset",
            "status": "idle",
            "dashboardUrl": "https://websets.exa.ai/websets/ws_123",
            "title": "Test Webset",
            "externalId": None,
            "searches": [],
            "enrichments": [],
            "monitors": [],
            "metadata": {},
            "createdAt": "2023-01-01T00:00:00Z",
            "updatedAt": "2023-01-01T00:00:00Z",
        },
    }


CASES = [
    pytest.param(
        MonitorsClient, AsyncMonitorsClient, "/websets/v0/monitors", _monitor,
        {"webset_id": "ws_123"}, {"websetId": "ws_123"},
        id="monitors",
    ),
    pytest.param(
        ImportsClient, AsyncImportsClient, "/websets/v0/imports", _import,
        {}, {},
        id="imports",
    ),
    pytest.param(
        EventsClient, AsyncEventsClient, "/websets/v0/events", _event,
        {"types": [EventType.webset_created]}, {"types": ["webset.created"]},
        id="events",
    ),
]


def _two_pages(make_item):
    """A first page that continues at cursor ``c2``, then the last page."""
    return [
        {"data": [make_item("first")], "hasMore": True, "nextCursor": "c2"},
        {"data": [make_item("second")], "hasMore": False, "nextCursor": None},
    ]


def _page_params(request_mock):
    return [call.kwargs["params"] for call in request_mock.call_args_list]


@pytest.mark.parametrize("sync_cls, async_cls, path, make_item, filters, filter_params", CASES)
def test_list_all_follows_the_cursor_and_keeps_the_filters(
    sync_cls, async_cls, path, make_item, filters, filter_params
):
    parent = MagicMock()
    parent.request.side_effect = _two_pages(make_item)

    items = list(sync_cls(parent).list_all(limit=1, **filters))

    assert [item.id for item in items] == ["first", "second"]
    assert [call.args[0] for call in parent.request.call_args_list] == [path, path]
    assert _page_params(parent.request) == [
        {"limit": 1, **filter_params},
        {"cursor": "c2", "limit": 1, **filter_params},
    ]


@pytest.mark.parametrize("sync_cls, async_cls, path, make_item, filters, filter_params", CASES)
def test_get_all_returns_every_page(sync_cls, async_cls, path, make_item, filters, filter_params):
    parent = MagicMock()
    parent.request.side_effect = _two_pages(make_item)

    items = sync_cls(parent).get_all(**filters)

    assert isinstance(items, list)
    assert [item.id for item in items] == ["first", "second"]


@pytest.mark.parametrize("sync_cls, async_cls, path, make_item, filters, filter_params", CASES)
def test_async_list_all_and_get_all_follow_the_cursor(
    sync_cls, async_cls, path, make_item, filters, filter_params
):
    parent = MagicMock()
    parent.async_request = AsyncMock(side_effect=_two_pages(make_item) + _two_pages(make_item))
    client = async_cls(parent)

    async def collect():
        listed = [item async for item in client.list_all(limit=1, **filters)]
        gathered = await client.get_all(limit=1, **filters)
        return listed, gathered

    listed, gathered = asyncio.run(collect())

    assert [item.id for item in listed] == ["first", "second"]
    assert [item.id for item in gathered] == ["first", "second"]
    assert _page_params(parent.async_request)[:2] == [
        {"limit": 1, **filter_params},
        {"cursor": "c2", "limit": 1, **filter_params},
    ]


@pytest.mark.parametrize("sync_cls, async_cls, path, make_item, filters, filter_params", CASES)
def test_a_cursor_in_extra_query_starts_the_listing_without_pinning_it(
    sync_cls, async_cls, path, make_item, filters, filter_params
):
    parent = MagicMock()
    parent.request.side_effect = _two_pages(make_item)

    items = sync_cls(parent).get_all(extra_query={"cursor": "c1", "debug": "1"}, **filters)

    assert [item.id for item in items] == ["first", "second"]
    extra_queries = [call.kwargs.get("extra_query") for call in parent.request.call_args_list]
    assert extra_queries == [{"cursor": "c1", "debug": "1"}, {"debug": "1"}]
