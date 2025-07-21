from datetime import datetime
import json
from typing import Dict, Any
from unittest.mock import MagicMock

import pytest

from exa_py.websets.events.client import EventsClient
from exa_py.websets.types import EventType

# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_response():
    """Factory fixture to create mock responses with custom data."""
    def _create_response(json_data: Dict[str, Any], status_code: int = 200) -> MagicMock:
        mock = MagicMock()
        mock.json_data = json_data
        mock.status_code = status_code
        mock.text = json.dumps(json_data)
        mock.json.return_value = json_data
        return mock
    return _create_response

@pytest.fixture
def parent_mock():
    """Mock parent client."""
    mock = MagicMock()
    return mock

@pytest.fixture
def events_client(parent_mock):
    """Create EventsClient with mocked parent."""
    return EventsClient(parent_mock)

@pytest.fixture
def sample_webset_data():
    """Sample complete webset data for events."""
    return {
        "id": "ws_123",
        "object": "webset",
        "status": "idle",
        "externalId": None,
        "searches": [],
        "enrichments": [],
        "monitors": [],
        "metadata": {},
        "createdAt": "2023-01-01T00:00:00Z",
        "updatedAt": "2023-01-01T00:00:00Z"
    }

@pytest.fixture
def sample_webset_item_data():
    """Sample complete webset item data for events."""
    return {
        "id": "item_456",
        "object": "webset_item",
        "source": "search",
        "sourceId": "search_123",
        "websetId": "ws_123",
        "properties": {
            "type": "company",
            "url": "https://example.com",
            "description": "Example company",
            "company": {
                "name": "Example Corp",
                "location": "San Francisco, CA"
            }
        },
        "evaluations": [],
        "enrichments": [],
        "createdAt": "2023-01-01T00:10:00Z",
        "updatedAt": "2023-01-01T00:10:00Z"
    }

@pytest.fixture
def sample_list_events_response(sample_webset_data, sample_webset_item_data):
    """Sample response for list events."""
    return {
        "data": [
            {
                "id": "event_123",
                "object": "event",
                "type": "webset.created",
                "createdAt": "2023-01-01T00:00:00Z",
                "data": sample_webset_data
            },
            {
                "id": "event_124",
                "object": "event",
                "type": "webset.idle",
                "createdAt": "2023-01-01T00:05:00Z",
                "data": sample_webset_data
            },
            {
                "id": "event_125",
                "object": "event",
                "type": "webset.item.created",
                "createdAt": "2023-01-01T00:10:00Z",
                "data": sample_webset_item_data
            }
        ],
        "hasMore": True,
        "nextCursor": "cursor_abc"
    }

@pytest.fixture
def sample_event_response(sample_webset_data):
    """Sample response for a single event."""
    return {
        "id": "event_123",
        "object": "event",
        "type": "webset.created",
        "createdAt": "2023-01-01T00:00:00Z",
        "data": sample_webset_data
    }

# ============================================================================
# EventsClient Tests
# ============================================================================

def test_list_events_basic(events_client, parent_mock, sample_list_events_response):
    """Test basic event listing."""
    parent_mock.request.return_value = sample_list_events_response

    result = events_client.list()

    # Verify the result
    assert len(result.data) == 3
    assert result.has_more is True
    assert result.next_cursor == "cursor_abc"
    assert result.data[0].type == "webset.created"
    assert result.data[1].type == "webset.idle"
    assert result.data[2].type == "webset.item.created"
    
    # Verify request was called correctly
    parent_mock.request.assert_called_once_with(
        "/websets/v0/events", 
        params={}, 
        method="GET",
        data=None
    )

def test_list_events_with_params(events_client, parent_mock, sample_list_events_response):
    """Test listing events with cursor, limit, and types."""
    parent_mock.request.return_value = sample_list_events_response

    result = events_client.list(
        cursor="cursor_xyz",
        limit=5,
        types=[EventType.webset_created, EventType.webset_idle]
    )

    # Verify request parameters
    parent_mock.request.assert_called_once_with(
        "/websets/v0/events",
        params={
            "cursor": "cursor_xyz",
            "limit": 5,
            "types": ["webset.created", "webset.idle"]
        },
        method="GET",
        data=None
    )

def test_list_events_with_single_type(events_client, parent_mock, sample_list_events_response):
    """Test listing events with a single type filter."""
    parent_mock.request.return_value = sample_list_events_response

    result = events_client.list(types=[EventType.webset_item_created])

    # Verify request parameters
    parent_mock.request.assert_called_once_with(
        "/websets/v0/events",
        params={
            "types": ["webset.item.created"]
        },
        method="GET",
        data=None
    )

def test_list_events_empty_response(events_client, parent_mock):
    """Test listing events with empty response."""
    empty_response = {
        "data": [],
        "hasMore": False,
        "nextCursor": None
    }
    parent_mock.request.return_value = empty_response

    result = events_client.list()

    assert len(result.data) == 0
    assert result.has_more is False
    assert result.next_cursor is None

def test_get_event(events_client, parent_mock, sample_event_response):
    """Test getting a single event."""
    parent_mock.request.return_value = sample_event_response

    result = events_client.get("event_123")

    # Verify the result
    assert result.id == "event_123"
    assert result.type == "webset.created"
    
    # Verify request was called correctly
    parent_mock.request.assert_called_once_with(
        "/websets/v0/events/event_123",
        method="GET",
        data=None,
        params=None
    )

def test_get_event_different_types(events_client, parent_mock, sample_webset_data, sample_webset_item_data):
    """Test getting events of different types."""
    # Create sample search data
    sample_search_data = {
        "id": "search_123",
        "object": "webset_search",
        "websetId": "webset_123",
        "status": "completed",
        "query": "test query",
        "entity": {"type": "company"},
        "criteria": [],
        "count": 10,
        "behavior": "override",
        "progress": {"found": 10, "completion": 100.0},
        "metadata": {},
        "canceledAt": None,
        "canceledReason": None,
        "createdAt": "2023-01-01T00:00:00Z",
        "updatedAt": "2023-01-01T00:00:00Z"
    }
    
    event_types = [
        ("webset.deleted", "event_deleted", sample_webset_data),
        ("webset.idle", "event_idle", sample_webset_data),
        ("webset.paused", "event_paused", sample_webset_data),
        ("webset.item.enriched", "event_enriched", sample_webset_item_data),
        ("webset.search.created", "event_search_created", sample_search_data),
        ("webset.search.updated", "event_search_updated", sample_search_data),
        ("webset.search.canceled", "event_search_canceled", sample_search_data),
        ("webset.search.completed", "event_search_completed", sample_search_data),
    ]
    
    for event_type, event_id, event_data in event_types:
        response = {
            "id": event_id,
            "object": "event",
            "type": event_type,
            "createdAt": "2023-01-01T00:00:00Z",
            "data": event_data
        }
        parent_mock.request.return_value = response
        
        result = events_client.get(event_id)
        assert result.id == event_id
        assert result.type == event_type

def test_get_event_unknown_type(events_client, parent_mock):
    """Test getting an event with unknown type raises error."""
    unknown_event = {
        "id": "event_unknown",
        "object": "event",
        "type": "unknown.type",
        "createdAt": "2023-01-01T00:00:00Z",
        "data": {}
    }
    parent_mock.request.return_value = unknown_event

    with pytest.raises(ValueError, match="Unknown event type: unknown.type"):
        events_client.get("event_unknown")

def test_list_events_type_enum_handling(events_client, parent_mock, sample_list_events_response):
    """Test that EventType enums are properly converted to string values."""
    parent_mock.request.return_value = sample_list_events_response
    
    # Test with various EventType enums
    types = [
        EventType.webset_created,
        EventType.webset_item_created,
        EventType.webset_search_completed
    ]
    
    events_client.list(types=types)
    
    # Verify the enum values were converted to strings
    expected_types = ["webset.created", "webset.item.created", "webset.search.completed"]
    parent_mock.request.assert_called_once_with(
        "/websets/v0/events",
        params={"types": expected_types},
        method="GET",
        data=None
    )

# ============================================================================
# Error Handling Tests
# ============================================================================

def test_list_events_request_error(events_client, parent_mock):
    """Test that client properly handles request errors on list."""
    parent_mock.request.side_effect = Exception("Network error")
    
    with pytest.raises(Exception, match="Network error"):
        events_client.list()

def test_get_event_not_found(events_client, parent_mock):
    """Test handling of event not found error."""
    parent_mock.request.side_effect = Exception("Event not found")
    
    with pytest.raises(Exception, match="Event not found"):
        events_client.get("nonexistent_event")

# ============================================================================
# Case Conversion Tests
# ============================================================================

def test_case_conversion_in_event_response(events_client, parent_mock, sample_webset_data):
    """Test that camelCase fields are properly converted to snake_case."""
    # Add externalId to the webset data
    webset_data_with_external = sample_webset_data.copy()
    webset_data_with_external["externalId"] = "external_123"
    
    response = {
        "id": "event_case",
        "object": "event",
        "type": "webset.created",
        "createdAt": "2023-01-01T00:00:00Z",
        "data": webset_data_with_external
    }
    parent_mock.request.return_value = response
    
    result = events_client.get("event_case")
    
    # Verify the response properly maps camelCase to snake_case
    assert result.created_at is not None  # createdAt -> created_at
    assert hasattr(result, 'created_at')
    
    # Verify data field conversion if applicable
    if hasattr(result.data, 'id'):
        assert result.data.id == "ws_123"
    if hasattr(result.data, 'external_id'):
        assert result.data.external_id == "external_123"  # externalId -> external_id

# ============================================================================
# Edge Cases and Additional Coverage
# ============================================================================

def test_list_events_with_none_cursor(events_client, parent_mock, sample_list_events_response):
    """Test listing events with explicit None cursor."""
    parent_mock.request.return_value = sample_list_events_response
    
    result = events_client.list(cursor=None, limit=None)
    
    # Verify result is returned
    assert result is not None
    assert len(result.data) == 3
    
    # Should not include None values in params
    parent_mock.request.assert_called_once_with(
        "/websets/v0/events",
        params={},
        method="GET",
        data=None
    )

def test_list_events_pagination_flow(events_client, parent_mock, sample_webset_data):
    """Test paginating through multiple pages of events."""
    # First page
    first_page = {
        "data": [
            {
                "id": "event_1",
                "object": "event",
                "type": "webset.created",
                "createdAt": "2023-01-01T00:00:00Z",
                "data": sample_webset_data
            }
        ],
        "hasMore": True,
        "nextCursor": "cursor_page2"
    }
    
    # Second page
    second_page = {
        "data": [
            {
                "id": "event_2",
                "object": "event",
                "type": "webset.idle",
                "createdAt": "2023-01-01T00:01:00Z",
                "data": sample_webset_data
            }
        ],
        "hasMore": False,
        "nextCursor": None
    }
    
    parent_mock.request.side_effect = [first_page, second_page]
    
    # Get first page
    result1 = events_client.list(limit=1)
    assert len(result1.data) == 1
    assert result1.has_more is True
    assert result1.next_cursor == "cursor_page2"
    
    # Get second page using cursor from first
    result2 = events_client.list(cursor=result1.next_cursor, limit=1)
    assert len(result2.data) == 1
    assert result2.has_more is False
    assert result2.next_cursor is None
    
    # Verify both requests were made correctly
    assert parent_mock.request.call_count == 2