"""Tests for async websets client functionality."""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any
from unittest.mock import MagicMock, AsyncMock
from unittest import IsolatedAsyncioTestCase

import pytest
from pydantic import AnyUrl

from exa_py.websets.async_client import AsyncWebsetsClient
from exa_py.websets.core.async_base import WebsetsAsyncBaseClient
from exa_py.websets.async_items.client import AsyncWebsetItemsClient
from exa_py.websets.async_searches.client import AsyncWebsetSearchesClient
from exa_py.websets.async_enrichments.client import AsyncWebsetEnrichmentsClient
from exa_py.websets.async_webhooks.client import AsyncWebsetWebhooksClient
from exa_py.websets.async_monitors.client import AsyncMonitorsClient
from exa_py.websets.async_imports.client import AsyncImportsClient
from exa_py.websets.async_events.client import AsyncEventsClient
from exa_py.websets.types import (
    UpdateWebsetRequest,
    CreateWebsetParameters,
    CreateWebsetParametersSearch,
    CreateEnrichmentParameters,
    Format,
    WebsetStatus,
    EventType
)

# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_async_response():
    """Factory fixture to create mock async responses with custom data."""
    def _create_response(json_data: Dict[str, Any], status_code: int = 200) -> MagicMock:
        mock = MagicMock()
        mock.json_data = json_data
        mock.status_code = status_code
        mock.text = json.dumps(json_data)
        mock.json.return_value = json_data
        return mock
    return _create_response

@pytest.fixture
def async_parent_mock():
    """Create a mock async parent client."""
    mock = MagicMock()
    mock.async_request = AsyncMock()
    return mock

@pytest.fixture
def async_base_client(async_parent_mock):
    """Create an async base client instance with mock parent."""
    return WebsetsAsyncBaseClient(async_parent_mock)

@pytest.fixture
def async_websets_client(async_parent_mock):
    """Create an AsyncWebsetsClient instance with mock parent."""
    return AsyncWebsetsClient(async_parent_mock)

@pytest.fixture
def async_items_client(async_websets_client):
    """Create an async items client instance."""
    return async_websets_client.items

@pytest.fixture
def sample_webset_data():
    """Sample webset data for testing."""
    return {
        "id": "ws_123",
        "object": "webset",
        "status": "idle",
        "externalId": "test-id",
        "createdAt": "2023-01-01T00:00:00Z",
        "updatedAt": "2023-01-01T00:00:00Z",
        "searches": [],
        "enrichments": [],
        "monitors": []
    }

@pytest.fixture
def sample_webset_items_data():
    """Sample webset items data for testing."""
    return {
        "data": [
            {
                "id": "item_123",
                "object": "webset_item",
                "source": "search",
                "sourceId": "search_123",
                "websetId": "ws_123",
                "properties": {
                    "type": "company",
                    "url": "https://example.com",
                    "description": "This is a test description",
                    "company": {
                        "name": "Example Company",
                        "logoUrl": "https://example.com/logo.png",
                    }
                },
                "evaluations": [],
                "enrichments": [],
                "createdAt": "2023-01-01T00:00:00Z",
                "updatedAt": "2023-01-01T00:00:00Z"
            }
        ],
        "hasMore": False,
        "nextCursor": None
    }

# ============================================================================
# Async Base Client Tests
# ============================================================================

@pytest.mark.asyncio
async def test_async_base_client_request_forwards_to_parent(async_base_client, async_parent_mock):
    """Test that AsyncWebsetsBaseClient.request forwards to the parent client's async_request method."""
    async_parent_mock.async_request.return_value = {"key": "value"}
    
    result = await async_base_client.request(
        "/test",
        data={"param": "value"},
        method="POST",
        params={"query": "test"}
    )
    
    async_parent_mock.async_request.assert_called_once_with(
        "/websets/test",
        data={"param": "value"},
        method="POST",
        params={"query": "test"}
    )
    
    assert result == {"key": "value"}

@pytest.mark.asyncio
async def test_async_base_client_data_preparation(async_base_client, async_parent_mock):
    """Test that async base client properly prepares different data types."""
    async_parent_mock.async_request.return_value = {"success": True}
    
    # Test with dict
    await async_base_client.request("/test", data={"key": "value"})
    call_args = async_parent_mock.async_request.call_args
    assert call_args[1]["data"] == {"key": "value"}
    
    # Test with model instance
    async_parent_mock.async_request.reset_mock()
    model_params = CreateWebsetParameters(
        search=CreateWebsetParametersSearch(query="test", count=10)
    )
    await async_base_client.request("/test", data=model_params)
    
    call_args = async_parent_mock.async_request.call_args
    assert "search" in call_args[1]["data"]
    assert call_args[1]["data"]["search"]["query"] == "test"

# ============================================================================
# Async Main Client Tests
# ============================================================================

@pytest.mark.asyncio
async def test_async_websets_client_create(async_websets_client, async_parent_mock, sample_webset_data):
    """Test async webset creation."""
    async_parent_mock.async_request.return_value = sample_webset_data
    
    params = CreateWebsetParameters(
        external_id="test-id",
        search=CreateWebsetParametersSearch(query="test query", count=10)
    )
    
    result = await async_websets_client.create(params=params)
    
    async_parent_mock.async_request.assert_called_once_with(
        "/websets/v0/websets", 
        data=params, 
        method="POST", 
        params=None
    )
    assert result.id == "ws_123"
    assert result.external_id == "test-id"

@pytest.mark.asyncio
async def test_async_websets_client_get(async_websets_client, async_parent_mock, sample_webset_data):
    """Test async webset retrieval."""
    async_parent_mock.async_request.return_value = sample_webset_data
    
    result = await async_websets_client.get(id="ws_123")
    
    async_parent_mock.async_request.assert_called_once_with(
        "/websets/v0/websets/ws_123",
        params={},
        method="GET",
        data=None
    )
    assert result.id == "ws_123"
    assert result.status == "idle"

@pytest.mark.asyncio
async def test_async_websets_client_get_with_expand(async_websets_client, async_parent_mock, sample_webset_data):
    """Test async webset retrieval with expand parameter."""
    async_parent_mock.async_request.return_value = sample_webset_data
    
    result = await async_websets_client.get(id="ws_123", expand=["items"])
    
    async_parent_mock.async_request.assert_called_once_with(
        "/websets/v0/websets/ws_123",
        params={"expand": ["items"]},
        method="GET",
        data=None
    )
    assert result.id == "ws_123"

@pytest.mark.asyncio
async def test_async_websets_client_list(async_websets_client, async_parent_mock, sample_webset_data):
    """Test async websets listing."""
    list_response = {
        "data": [sample_webset_data],
        "hasMore": False,
        "nextCursor": None
    }
    async_parent_mock.async_request.return_value = list_response
    
    result = await async_websets_client.list(cursor="test_cursor", limit=10)
    
    async_parent_mock.async_request.assert_called_once_with(
        "/websets/v0/websets",
        params={"cursor": "test_cursor", "limit": 10},
        method="GET",
        data=None
    )
    assert len(result.data) == 1
    assert result.data[0].id == "ws_123"

@pytest.mark.asyncio
async def test_async_websets_client_update(async_websets_client, async_parent_mock, sample_webset_data):
    """Test async webset update."""
    updated_data = {**sample_webset_data, "status": "running"}
    async_parent_mock.async_request.return_value = updated_data
    
    params = UpdateWebsetRequest(metadata={"updated": "true"})
    result = await async_websets_client.update(id="ws_123", params=params)
    
    async_parent_mock.async_request.assert_called_once_with(
        "/websets/v0/websets/ws_123",
        data=params,
        method="POST",
        params=None
    )
    assert result.id == "ws_123"

@pytest.mark.asyncio
async def test_async_websets_client_delete(async_websets_client, async_parent_mock, sample_webset_data):
    """Test async webset deletion."""
    async_parent_mock.async_request.return_value = sample_webset_data
    
    result = await async_websets_client.delete(id="ws_123")
    
    async_parent_mock.async_request.assert_called_once_with(
        "/websets/v0/websets/ws_123",
        method="DELETE",
        data=None,
        params=None
    )
    assert result.id == "ws_123"

@pytest.mark.asyncio
async def test_async_websets_client_cancel(async_websets_client, async_parent_mock, sample_webset_data):
    """Test async webset cancellation."""
    async_parent_mock.async_request.return_value = sample_webset_data
    
    result = await async_websets_client.cancel(id="ws_123")
    
    async_parent_mock.async_request.assert_called_once_with(
        "/websets/v0/websets/ws_123/cancel",
        method="POST",
        data=None,
        params=None
    )
    assert result.id == "ws_123"

@pytest.mark.asyncio
async def test_async_websets_client_preview(async_websets_client, async_parent_mock):
    """Test async webset preview."""
    preview_response = {
        "search": {
            "entity": {"type": "company"},
            "criteria": [{"description": "AI companies"}]
        },
        "enrichments": [{"description": "Valuation", "format": "number"}]
    }
    async_parent_mock.async_request.return_value = preview_response
    
    params = {"query": "AI companies founded after 2020"}
    result = await async_websets_client.preview(params)
    
    async_parent_mock.async_request.assert_called_once_with(
        "/websets/v0/websets/preview", 
        data=params, 
        method="POST", 
        params=None
    )
    assert result.search.entity.type == "company"

@pytest.mark.asyncio
async def test_async_dict_and_model_parameter_support(async_websets_client, async_parent_mock, sample_webset_data):
    """Test that async client methods accept both dictionaries and model instances."""
    async_parent_mock.async_request.return_value = sample_webset_data
    
    # Test with a model instance
    model_params = CreateWebsetParameters(
        search=CreateWebsetParametersSearch(query="Test query", count=10),
        enrichments=[CreateEnrichmentParameters(description="Test enrichment", format=Format.text)]
    )
    model_result = await async_websets_client.create(params=model_params)
    
    # Test with an equivalent dictionary
    dict_params = {
        "search": {"query": "Test query", "count": 10},
        "enrichments": [{"description": "Test enrichment", "format": "text"}]
    }
    dict_result = await async_websets_client.create(params=dict_params)
    
    # Verify both calls produce the same result
    assert model_result.id == dict_result.id
    assert model_result.status == dict_result.status
    
    # Verify both calls were made
    assert len(async_parent_mock.async_request.call_args_list) == 2

# ============================================================================
# Async Items Client Tests
# ============================================================================

@pytest.mark.asyncio
async def test_async_items_client_list(async_items_client, async_parent_mock, sample_webset_items_data):
    """Test async items listing."""
    async_parent_mock.async_request.return_value = sample_webset_items_data
    
    result = await async_items_client.list(
        webset_id="ws_123", 
        cursor="test_cursor", 
        limit=10, 
        source_id="search_123"
    )
    
    async_parent_mock.async_request.assert_called_once_with(
        "/websets/v0/websets/ws_123/items",
        params={"cursor": "test_cursor", "limit": 10, "sourceId": "search_123"},
        method="GET",
        data=None
    )
    assert len(result.data) == 1
    assert result.data[0].id == "item_123"
    assert result.data[0].properties.company.logo_url == AnyUrl("https://example.com/logo.png")

@pytest.mark.asyncio
async def test_async_items_client_list_all_single_page(async_items_client, async_parent_mock, sample_webset_items_data):
    """Test async items list_all generator with single page."""
    async_parent_mock.async_request.return_value = sample_webset_items_data
    
    items = []
    async for item in async_items_client.list_all(webset_id="ws_123", limit=100):
        items.append(item)
    
    assert len(items) == 1
    assert items[0].id == "item_123"
    async_parent_mock.async_request.assert_called_once()

@pytest.mark.asyncio
async def test_async_items_client_list_all_multiple_pages(async_items_client, async_parent_mock):
    """Test async items list_all generator with multiple pages."""
    # First page response
    first_page = {
        "data": [
            {"id": "item_1", "object": "webset_item", "source": "search", "sourceId": "search_123", 
             "websetId": "ws_123", "properties": {"type": "company"}, "evaluations": [], "enrichments": [],
             "createdAt": "2023-01-01T00:00:00Z", "updatedAt": "2023-01-01T00:00:00Z"}
        ],
        "hasMore": True,
        "nextCursor": "cursor_2"
    }
    
    # Second page response
    second_page = {
        "data": [
            {"id": "item_2", "object": "webset_item", "source": "search", "sourceId": "search_123", 
             "websetId": "ws_123", "properties": {"type": "company"}, "evaluations": [], "enrichments": [],
             "createdAt": "2023-01-01T00:00:00Z", "updatedAt": "2023-01-01T00:00:00Z"}
        ],
        "hasMore": False,
        "nextCursor": None
    }
    
    # Configure mock to return different responses for each call
    async_parent_mock.async_request.side_effect = [first_page, second_page]
    
    items = []
    async for item in async_items_client.list_all(webset_id="ws_123", limit=1):
        items.append(item)
    
    assert len(items) == 2
    assert items[0].id == "item_1"
    assert items[1].id == "item_2"
    assert async_parent_mock.async_request.call_count == 2
    
    # Verify first call had no cursor
    first_call = async_parent_mock.async_request.call_args_list[0]
    assert first_call[1]["params"]["cursor"] is None or "cursor" not in first_call[1]["params"]
    
    # Verify second call had cursor from first response
    second_call = async_parent_mock.async_request.call_args_list[1]
    assert second_call[1]["params"]["cursor"] == "cursor_2"

@pytest.mark.asyncio
async def test_async_items_client_get(async_items_client, async_parent_mock, sample_webset_items_data):
    """Test async item retrieval."""
    item_data = sample_webset_items_data["data"][0]
    async_parent_mock.async_request.return_value = item_data
    
    result = await async_items_client.get(webset_id="ws_123", id="item_123")
    
    async_parent_mock.async_request.assert_called_once_with(
        "/websets/v0/websets/ws_123/items/item_123",
        method="GET",
        data=None,
        params=None
    )
    assert result.id == "item_123"

@pytest.mark.asyncio
async def test_async_items_client_delete(async_items_client, async_parent_mock, sample_webset_items_data):
    """Test async item deletion."""
    item_data = sample_webset_items_data["data"][0]
    async_parent_mock.async_request.return_value = item_data
    
    result = await async_items_client.delete(webset_id="ws_123", id="item_123")
    
    async_parent_mock.async_request.assert_called_once_with(
        "/websets/v0/websets/ws_123/items/item_123",
        method="DELETE",
        data=None,
        params=None
    )
    assert result.id == "item_123"

# ============================================================================
# Async Polling Tests
# ============================================================================

@pytest.mark.asyncio
async def test_async_wait_until_idle_success(async_websets_client, async_parent_mock, sample_webset_data):
    """Test async wait_until_idle method succeeds when webset becomes idle."""
    # First call returns running status, second call returns idle
    running_data = {**sample_webset_data, "status": "running"}
    idle_data = {**sample_webset_data, "status": "idle"}
    
    async_parent_mock.async_request.side_effect = [running_data, idle_data]
    
    result = await async_websets_client.wait_until_idle("ws_123", timeout=10, poll_interval=1)
    
    assert result.status == "idle"
    assert async_parent_mock.async_request.call_count == 2

@pytest.mark.asyncio
async def test_async_wait_until_idle_timeout(async_websets_client, async_parent_mock, sample_webset_data):
    """Test async wait_until_idle method times out."""
    running_data = {**sample_webset_data, "status": "running"}
    async_parent_mock.async_request.return_value = running_data
    
    with pytest.raises(TimeoutError, match="did not become idle within 1 seconds"):
        await async_websets_client.wait_until_idle("ws_123", timeout=1, poll_interval=0.1)

@pytest.mark.asyncio
async def test_async_wait_until_idle_immediate(async_websets_client, async_parent_mock, sample_webset_data):
    """Test async wait_until_idle method when webset is already idle."""
    idle_data = {**sample_webset_data, "status": "idle"}
    async_parent_mock.async_request.return_value = idle_data
    
    result = await async_websets_client.wait_until_idle("ws_123", timeout=10, poll_interval=1)
    
    assert result.status == "idle"
    assert async_parent_mock.async_request.call_count == 1

# ============================================================================
# Async Sub-Clients Tests
# ============================================================================

@pytest.mark.asyncio
async def test_async_searches_client_create(async_websets_client, async_parent_mock):
    """Test async searches client creation."""
    search_response = {
        "id": "search_123",
        "object": "webset_search",
        "websetId": "ws_123",
        "status": "running",
        "query": "test query",
        "createdAt": "2023-01-01T00:00:00Z",
        "updatedAt": "2023-01-01T00:00:00Z"
    }
    async_parent_mock.async_request.return_value = search_response
    
    params = {"query": "test query", "count": 10}
    result = await async_websets_client.searches.create(webset_id="ws_123", params=params)
    
    async_parent_mock.async_request.assert_called_once_with(
        "/websets/v0/websets/ws_123/searches",
        data=params,
        method="POST",
        params=None
    )
    assert result.id == "search_123"
    assert result.query == "test query"

@pytest.mark.asyncio
async def test_async_searches_client_get(async_websets_client, async_parent_mock):
    """Test async searches client get."""
    search_response = {
        "id": "search_123",
        "object": "webset_search",
        "websetId": "ws_123",
        "status": "completed",
        "query": "test query",
        "createdAt": "2023-01-01T00:00:00Z",
        "updatedAt": "2023-01-01T00:00:00Z"
    }
    async_parent_mock.async_request.return_value = search_response
    
    result = await async_websets_client.searches.get(webset_id="ws_123", id="search_123")
    
    async_parent_mock.async_request.assert_called_once_with(
        "/websets/v0/websets/ws_123/searches/search_123",
        method="GET",
        data=None,
        params=None
    )
    assert result.id == "search_123"
    assert result.status == "completed"

@pytest.mark.asyncio
async def test_async_searches_client_cancel(async_websets_client, async_parent_mock):
    """Test async searches client cancel."""
    search_response = {
        "id": "search_123",
        "object": "webset_search",
        "websetId": "ws_123",
        "status": "canceled",
        "query": "test query",
        "createdAt": "2023-01-01T00:00:00Z",
        "updatedAt": "2023-01-01T00:00:00Z"
    }
    async_parent_mock.async_request.return_value = search_response
    
    result = await async_websets_client.searches.cancel(webset_id="ws_123", id="search_123")
    
    async_parent_mock.async_request.assert_called_once_with(
        "/websets/v0/websets/ws_123/searches/search_123/cancel",
        method="POST",
        data=None,
        params=None
    )
    assert result.id == "search_123"
    assert result.status == "canceled"

@pytest.mark.asyncio
async def test_async_enrichments_client_create(async_websets_client, async_parent_mock):
    """Test async enrichments client creation."""
    enrichment_response = {
        "id": "enrichment_123",
        "object": "webset_enrichment",
        "websetId": "ws_123",
        "status": "running",
        "description": "Test enrichment",
        "format": "text",
        "createdAt": "2023-01-01T00:00:00Z",
        "updatedAt": "2023-01-01T00:00:00Z"
    }
    async_parent_mock.async_request.return_value = enrichment_response
    
    params = CreateEnrichmentParameters(description="Test enrichment", format=Format.text)
    result = await async_websets_client.enrichments.create(webset_id="ws_123", params=params)
    
    async_parent_mock.async_request.assert_called_once_with(
        "/websets/v0/websets/ws_123/enrichments",
        data=params,
        method="POST",
        params=None
    )
    assert result.id == "enrichment_123"
    assert result.description == "Test enrichment"

@pytest.mark.asyncio
async def test_async_events_client_list(async_websets_client, async_parent_mock):
    """Test async events client list."""
    events_response = {
        "data": [
            {
                "id": "event_123",
                "object": "event", 
                "type": "webset.created",
                "createdAt": "2023-01-01T00:00:00Z",
                "data": {
                    "id": "ws_123",
                    "object": "webset",
                    "status": "idle"
                }
            }
        ],
        "hasMore": False,
        "nextCursor": None
    }
    async_parent_mock.async_request.return_value = events_response
    
    result = await async_websets_client.events.list(limit=10, types=[EventType.webset_created])
    
    async_parent_mock.async_request.assert_called_once_with(
        "/websets/v0/events",
        params={"limit": 10, "types": ["webset.created"]},
        method="GET",
        data=None
    )
    assert len(result.data) == 1
    assert result.data[0].id == "event_123"

@pytest.mark.asyncio 
async def test_async_webhooks_client_create(async_websets_client, async_parent_mock):
    """Test async webhooks client creation."""
    webhook_response = {
        "id": "webhook_123",
        "object": "webhook",
        "url": "https://example.com/webhook",
        "eventTypes": ["webset.created"],
        "status": "active",
        "createdAt": "2023-01-01T00:00:00Z",
        "updatedAt": "2023-01-01T00:00:00Z"
    }
    async_parent_mock.async_request.return_value = webhook_response
    
    params = {
        "url": "https://example.com/webhook",
        "eventTypes": ["webset.created"]
    }
    result = await async_websets_client.webhooks.create(params=params)
    
    async_parent_mock.async_request.assert_called_once_with(
        "/websets/v0/webhooks",
        data=params,
        method="POST",
        params=None
    )
    assert result.id == "webhook_123"
    assert result.url == "https://example.com/webhook"

@pytest.mark.asyncio
async def test_async_monitors_client_create(async_websets_client, async_parent_mock):
    """Test async monitors client creation."""
    monitor_response = {
        "id": "monitor_123",
        "object": "monitor",
        "websetId": "ws_123",
        "name": "Test Monitor",
        "status": "active",
        "schedule": {"frequency": "daily", "time": "09:00"},
        "createdAt": "2023-01-01T00:00:00Z",
        "updatedAt": "2023-01-01T00:00:00Z"
    }
    async_parent_mock.async_request.return_value = monitor_response
    
    params = {
        "websetId": "ws_123",
        "name": "Test Monitor",
        "schedule": {"frequency": "daily", "time": "09:00"}
    }
    result = await async_websets_client.monitors.create(params=params)
    
    async_parent_mock.async_request.assert_called_once_with(
        "/websets/v0/monitors",
        data=params,
        method="POST",
        params=None
    )
    assert result.id == "monitor_123"
    assert result.name == "Test Monitor"

@pytest.mark.asyncio
async def test_async_imports_client_create_without_csv(async_websets_client, async_parent_mock):
    """Test async imports client creation without CSV data."""
    import_response = {
        "id": "import_123",
        "object": "import",
        "websetId": "ws_123",
        "status": "pending",
        "uploadUrl": "https://upload.example.com/import_123",
        "createdAt": "2023-01-01T00:00:00Z",
        "updatedAt": "2023-01-01T00:00:00Z"
    }
    async_parent_mock.async_request.return_value = import_response
    
    params = {
        "websetId": "ws_123",
        "name": "Test Import",
        "size": 1024,
        "count": 100
    }
    result = await async_websets_client.imports.create(params=params)
    
    async_parent_mock.async_request.assert_called_once_with(
        "/websets/v0/imports",
        data=params,
        method="POST",
        params=None
    )
    assert result.id == "import_123"
    assert result.upload_url == "https://upload.example.com/import_123"

@pytest.mark.asyncio
async def test_async_imports_client_wait_until_completed_success(async_websets_client, async_parent_mock):
    """Test async imports client wait_until_completed method succeeds."""
    # First call returns processing status, second call returns completed
    processing_data = {
        "id": "import_123",
        "object": "import",
        "status": "processing",
        "createdAt": "2023-01-01T00:00:00Z",
        "updatedAt": "2023-01-01T00:00:00Z"
    }
    completed_data = {
        "id": "import_123",
        "object": "import", 
        "status": "completed",
        "createdAt": "2023-01-01T00:00:00Z",
        "updatedAt": "2023-01-01T00:00:00Z"
    }
    
    async_parent_mock.async_request.side_effect = [processing_data, completed_data]
    
    result = await async_websets_client.imports.wait_until_completed("import_123", timeout=10, poll_interval=1)
    
    assert result.status == "completed"
    assert async_parent_mock.async_request.call_count == 2

@pytest.mark.asyncio
async def test_async_imports_client_wait_until_completed_timeout(async_websets_client, async_parent_mock):
    """Test async imports client wait_until_completed method times out."""
    processing_data = {
        "id": "import_123",
        "object": "import",
        "status": "processing",
        "createdAt": "2023-01-01T00:00:00Z",
        "updatedAt": "2023-01-01T00:00:00Z"
    }
    async_parent_mock.async_request.return_value = processing_data
    
    with pytest.raises(TimeoutError, match="did not complete within 1 seconds"):
        await async_websets_client.imports.wait_until_completed("import_123", timeout=1, poll_interval=0.1)

# ============================================================================
# Async Error Handling Tests
# ============================================================================

@pytest.mark.asyncio
async def test_async_base_client_invalid_data_type(async_base_client):
    """Test async base client raises TypeError for invalid data types."""
    with pytest.raises(TypeError, match="Expected dict, ExaBaseModel, or str"):
        await async_base_client._prepare_data(123)  # Invalid type

@pytest.mark.asyncio
async def test_async_client_initialization(async_parent_mock):
    """Test async client properly initializes all sub-clients."""
    client = AsyncWebsetsClient(async_parent_mock)
    
    assert isinstance(client.items, AsyncWebsetItemsClient)
    assert isinstance(client.searches, AsyncWebsetSearchesClient)
    assert isinstance(client.enrichments, AsyncWebsetEnrichmentsClient)
    assert isinstance(client.webhooks, AsyncWebsetWebhooksClient)
    assert isinstance(client.monitors, AsyncMonitorsClient)
    assert isinstance(client.imports, AsyncImportsClient)
    assert isinstance(client.events, AsyncEventsClient)
    
    # Verify all sub-clients have the same parent
    assert client.items._client == async_parent_mock
    assert client.searches._client == async_parent_mock
    assert client.enrichments._client == async_parent_mock

@pytest.mark.asyncio 
async def test_async_concurrent_requests(async_websets_client, async_parent_mock, sample_webset_data):
    """Test that async client can handle concurrent requests properly."""
    # Configure mock to return data for concurrent calls
    async_parent_mock.async_request.return_value = sample_webset_data
    
    # Execute multiple concurrent requests
    tasks = [
        async_websets_client.get("ws_123"),
        async_websets_client.get("ws_124"), 
        async_websets_client.get("ws_125")
    ]
    
    results = await asyncio.gather(*tasks)
    
    # Verify all requests completed successfully
    assert len(results) == 3
    assert all(result.id == "ws_123" for result in results)
    assert async_parent_mock.async_request.call_count == 3

@pytest.mark.asyncio
async def test_async_items_list_all_empty_result(async_items_client, async_parent_mock):
    """Test async items list_all generator with empty result."""
    empty_response = {
        "data": [],
        "hasMore": False,
        "nextCursor": None
    }
    async_parent_mock.async_request.return_value = empty_response
    
    items = []
    async for item in async_items_client.list_all(webset_id="ws_123"):
        items.append(item)
    
    assert len(items) == 0
    async_parent_mock.async_request.assert_called_once()

@pytest.mark.asyncio
async def test_async_items_list_all_early_break(async_items_client, async_parent_mock):
    """Test async items list_all generator with early break."""
    # Multi-page response setup
    first_page = {
        "data": [
            {"id": "item_1", "object": "webset_item", "source": "search", "sourceId": "search_123", 
             "websetId": "ws_123", "properties": {"type": "company"}, "evaluations": [], "enrichments": [],
             "createdAt": "2023-01-01T00:00:00Z", "updatedAt": "2023-01-01T00:00:00Z"},
            {"id": "item_2", "object": "webset_item", "source": "search", "sourceId": "search_123", 
             "websetId": "ws_123", "properties": {"type": "company"}, "evaluations": [], "enrichments": [],
             "createdAt": "2023-01-01T00:00:00Z", "updatedAt": "2023-01-01T00:00:00Z"}
        ],
        "hasMore": True,
        "nextCursor": "cursor_2"
    }
    
    async_parent_mock.async_request.return_value = first_page
    
    items = []
    async for item in async_items_client.list_all(webset_id="ws_123"):
        items.append(item)
        if len(items) >= 1:  # Break after first item
            break
    
    assert len(items) == 1
    assert items[0].id == "item_1"
    # Should only make one request since we broke early
    assert async_parent_mock.async_request.call_count == 1

@pytest.mark.asyncio
async def test_async_parameter_none_filtering(async_websets_client, async_parent_mock, sample_webset_data):
    """Test that None parameters are properly filtered in async requests."""
    list_response = {"data": [sample_webset_data], "hasMore": False, "nextCursor": None}
    async_parent_mock.async_request.return_value = list_response
    
    # Call with None parameters that should be filtered out
    result = await async_websets_client.list(cursor=None, limit=None)
    
    # Verify None values were filtered from params
    call_args = async_parent_mock.async_request.call_args
    assert call_args[1]["params"] == {}

@pytest.mark.asyncio
async def test_async_endpoint_url_construction(async_base_client, async_parent_mock):
    """Test that async base client constructs URLs correctly."""
    async_parent_mock.async_request.return_value = {"test": "data"}
    
    # Test with leading slash (should be removed)
    await async_base_client.request("/v0/test")
    call_args = async_parent_mock.async_request.call_args
    assert call_args[0][0] == "/websets/v0/test"
    
    # Test without leading slash
    async_parent_mock.async_request.reset_mock()
    await async_base_client.request("v0/test2")
    call_args = async_parent_mock.async_request.call_args
    assert call_args[0][0] == "/websets/v0/test2"

# ============================================================================
# Async Format Validation Tests
# ============================================================================

@pytest.mark.asyncio
async def test_async_format_validation_string_and_enum(async_websets_client, async_parent_mock):
    """Test that async format field accepts both string and enum values."""
    enrichment_response = {
        "id": "enrichment_123",
        "object": "webset_enrichment", 
        "websetId": "ws_123",
        "status": "running",
        "description": "Test enrichment",
        "format": "text",
        "createdAt": "2023-01-01T00:00:00Z",
        "updatedAt": "2023-01-01T00:00:00Z"
    }
    async_parent_mock.async_request.return_value = enrichment_response
    
    # Test with enum value
    params1 = CreateEnrichmentParameters(
        description="Test description",
        format=Format.text
    )
    result1 = await async_websets_client.enrichments.create(webset_id="ws_123", params=params1)
    
    # Test with string value
    async_parent_mock.async_request.reset_mock()
    async_parent_mock.async_request.return_value = enrichment_response
    
    params2 = CreateEnrichmentParameters(
        description="Test description", 
        format="text"
    )
    result2 = await async_websets_client.enrichments.create(webset_id="ws_123", params=params2)
    
    # Both should work and return the same result
    assert result1.format == result2.format
    assert async_parent_mock.async_request.call_count == 2
