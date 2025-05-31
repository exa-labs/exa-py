from datetime import datetime
import json
from typing import Dict, Any

import pytest
from unittest.mock import MagicMock

from exa_py.websets.streams.client import StreamsClient
from exa_py.websets.streams.runs.client import StreamRunsClient
from exa_py.websets.types import (
    CreateStreamParameters,
    UpdateStream,
    StreamBehaviorSearch,
    StreamBehaviorRefresh,
    StreamBehaviorSearchConfig,
    StreamRefreshBehaviorEnrichmentsConfig,
    StreamRefreshBehaviorContentsConfig,
    StreamCadence,
    StreamStatus,
    WebsetCompanyEntity,
)

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
    """Create a mock parent client."""
    return MagicMock()

@pytest.fixture
def streams_client(parent_mock):
    """Create a StreamsClient instance with mock parent."""
    return StreamsClient(parent_mock)

@pytest.fixture
def runs_client(parent_mock):
    """Create a StreamRunsClient instance with mock parent."""
    return StreamRunsClient(parent_mock)

@pytest.fixture
def sample_stream_response():
    """Sample stream response data."""
    return {
        "id": "stream_123",
        "object": "stream",
        "status": "open",
        "websetId": "ws_123",
        "cadence": {
            "cron": "0 9 * * *",  # Daily at 9:00 AM
            "timezone": "Etc/UTC"
        },
        "behavior": {
            "type": "search",
            "config": {
                "query": "AI startups",
                "criteria": [{"description": "Must be AI focused"}],
                "entity": {"type": "company"},
                "count": 10,
                "behavior": "append"
            }
        },
        "lastRun": {
            "id": "run_123",
            "object": "stream_run",
            "status": "completed",
            "streamId": "stream_123",
            "type": "search",
            "completedAt": "2023-01-01T10:00:00Z",
            "failedAt": None,
            "canceledAt": None,
            "createdAt": "2023-01-01T09:00:00Z",
            "updatedAt": "2023-01-01T10:00:00Z"
        },
        "nextRunAt": "2023-01-02T09:00:00Z",
        "metadata": {"key": "value"},
        "createdAt": "2023-01-01T00:00:00Z",
        "updatedAt": "2023-01-01T00:00:00Z"
    }

@pytest.fixture
def sample_stream_run_response():
    """Sample stream run response data."""
    return {
        "id": "run_123",
        "object": "stream_run",
        "status": "completed",
        "streamId": "stream_123",
        "type": "search",
        "completedAt": "2023-01-01T10:00:00Z",
        "failedAt": None,
        "canceledAt": None,
        "createdAt": "2023-01-01T09:00:00Z",
        "updatedAt": "2023-01-01T10:00:00Z"
    }

# ============================================================================
# StreamsClient Tests
# ============================================================================

def test_streams_client_has_runs_client(streams_client):
    """Test that StreamsClient properly initializes with a runs client."""
    assert hasattr(streams_client, 'runs')
    assert isinstance(streams_client.runs, StreamRunsClient)

def test_create_stream_with_search_behavior(streams_client, parent_mock, sample_stream_response):
    """Test creating a stream with search behavior."""
    parent_mock.request.return_value = sample_stream_response
    
    # Create parameters with search behavior
    params = CreateStreamParameters(
        webset_id="ws_123",
        cadence=StreamCadence(
            cron="0 9 * * *",  # Daily at 9:00 AM
            timezone="America/New_York"
        ),
        behavior=StreamBehaviorSearch(
            type="search",
            config=StreamBehaviorSearchConfig(
                query="AI startups",
                criteria=[{"description": "Must be AI focused"}],
                entity=WebsetCompanyEntity(type="company"),
                count=10
            )
        ),
        metadata={"environment": "test"}
    )
    
    result = streams_client.create(params)
    
    # Verify the request was made correctly
    parent_mock.request.assert_called_once_with(
        "/websets/v0/streams",
        data=params.model_dump(by_alias=True, exclude_none=True),
        method="POST",
        params=None
    )
    
    # Verify the response
    assert result.id == "stream_123"
    assert result.webset_id == "ws_123"
    assert result.status == "open"

def test_create_stream_with_refresh_behavior(streams_client, parent_mock, sample_stream_response):
    """Test creating a stream with refresh behavior."""
    # Modify response for refresh behavior
    refresh_response = sample_stream_response.copy()
    refresh_response["behavior"] = {
        "type": "refresh",
        "config": {
            "target": "enrichments",
            "enrichments": {"ids": ["enrich_123"]}
        }
    }
    parent_mock.request.return_value = refresh_response
    
    params = CreateStreamParameters(
        webset_id="ws_123",
        cadence=StreamCadence(cron="0 9 * * 1"),  # Weekly on Monday at 9:00 AM
        behavior=StreamBehaviorRefresh(
            type="refresh",
            config=StreamRefreshBehaviorEnrichmentsConfig(
                target="enrichments",
                enrichments={"ids": ["enrich_123"]}
            )
        )
    )
    
    result = streams_client.create(params)
    
    assert result.id == "stream_123"
    assert result.behavior.type == "refresh"

def test_create_stream_with_contents_refresh(streams_client, parent_mock, sample_stream_response):
    """Test creating a stream with contents refresh behavior."""
    # Modify response for contents refresh
    refresh_response = sample_stream_response.copy()
    refresh_response["behavior"] = {
        "type": "refresh",
        "config": {
            "target": "contents"
        }
    }
    parent_mock.request.return_value = refresh_response
    
    params = CreateStreamParameters(
        webset_id="ws_123",
        cadence=StreamCadence(cron="0 9 1 * *"),  # Monthly on the 1st at 9:00 AM
        behavior=StreamBehaviorRefresh(
            type="refresh",
            config=StreamRefreshBehaviorContentsConfig(target="contents")
        )
    )
    
    result = streams_client.create(params)
    
    assert result.id == "stream_123"
    assert result.behavior.type == "refresh"

def test_create_stream_with_dict_params(streams_client, parent_mock, sample_stream_response):
    """Test creating a stream with dictionary parameters."""
    parent_mock.request.return_value = sample_stream_response
    
    dict_params = {
        "websetId": "ws_123",
        "cadence": {
            "cron": "0 10 * * *",  # Daily at 10:00 AM
            "timezone": "UTC"
        },
        "behavior": {
            "type": "search",
            "config": {
                "query": "tech companies",
                "criteria": [{"description": "Technology focused"}],
                "entity": {"type": "company"},
                "count": 20
            }
        }
    }
    
    result = streams_client.create(dict_params)
    
    assert result.id == "stream_123"
    parent_mock.request.assert_called_once_with("/websets/v0/streams", data=dict_params, method="POST", params=None)

def test_get_stream(streams_client, parent_mock, sample_stream_response):
    """Test getting a specific stream."""
    parent_mock.request.return_value = sample_stream_response
    
    result = streams_client.get("stream_123")
    
    parent_mock.request.assert_called_once_with(
        "/websets/v0/streams/stream_123",
        data=None,
        method="GET",
        params=None
    )
    
    assert result.id == "stream_123"
    assert result.status == "open"

def test_list_streams(streams_client, parent_mock):
    """Test listing streams with pagination."""
    mock_response = {
        "data": [
            {
                "id": "stream_123",
                "object": "stream",
                "status": "open",
                "websetId": "ws_123",
                "cadence": {"cron": "0 9 * * *"},  # Daily at 9:00 AM
                "behavior": {"type": "search", "config": {"query": "test", "criteria": [], "entity": {"type": "company"}, "count": 10}},
                "lastRun": None,
                "nextRunAt": "2023-01-02T09:00:00Z",
                "metadata": {},
                "createdAt": "2023-01-01T00:00:00Z",
                "updatedAt": "2023-01-01T00:00:00Z"
            }
        ],
        "hasMore": True,
        "nextCursor": "cursor_123"
    }
    parent_mock.request.return_value = mock_response
    
    result = streams_client.list(cursor="prev_cursor", limit=10, webset_id="ws_123")
    
    parent_mock.request.assert_called_once_with(
        "/websets/v0/streams",
        data=None,
        method="GET",
        params={"cursor": "prev_cursor", "limit": 10, "websetId": "ws_123"}
    )
    
    assert len(result.data) == 1
    assert result.data[0].id == "stream_123"
    assert result.has_more is True
    assert result.next_cursor == "cursor_123"

def test_list_streams_no_params(streams_client, parent_mock):
    """Test listing streams without optional parameters."""
    mock_response = {
        "data": [],
        "hasMore": False,
        "nextCursor": None
    }
    parent_mock.request.return_value = mock_response
    
    result = streams_client.list()
    
    parent_mock.request.assert_called_once_with(
        "/websets/v0/streams",
        data=None,
        method="GET",
        params={}
    )
    
    assert len(result.data) == 0
    assert result.has_more is False
    assert result.next_cursor is None

def test_update_stream(streams_client, parent_mock, sample_stream_response):
    """Test updating a stream."""
    updated_response = sample_stream_response.copy()
    updated_response["status"] = "closed"
    updated_response["metadata"] = {"updated": "true"}
    
    parent_mock.request.return_value = updated_response
    
    update_params = UpdateStream(
        status=StreamStatus.closed,
        metadata={"updated": "true"}
    )
    
    result = streams_client.update("stream_123", update_params)
    
    parent_mock.request.assert_called_once_with(
        "/websets/v0/streams/stream_123",
        data=update_params.model_dump(by_alias=True, exclude_none=True),
        method="PATCH",
        params=None
    )
    
    assert result.status == "closed"
    assert result.metadata["updated"] == "true"

def test_update_stream_with_dict(streams_client, parent_mock, sample_stream_response):
    """Test updating a stream with dictionary parameters."""
    updated_response = sample_stream_response.copy()
    updated_response["status"] = "closed"
    
    parent_mock.request.return_value = updated_response
    
    dict_params = {"status": "closed"}
    
    result = streams_client.update("stream_123", dict_params)
    
    parent_mock.request.assert_called_once_with(
        "/websets/v0/streams/stream_123",
        data=dict_params,
        method="PATCH",
        params=None
    )
    
    assert result.status == "closed"

def test_delete_stream(streams_client, parent_mock, sample_stream_response):
    """Test deleting a stream."""
    parent_mock.request.return_value = sample_stream_response
    
    result = streams_client.delete("stream_123")
    
    parent_mock.request.assert_called_once_with(
        "/websets/v0/streams/stream_123",
        data=None,
        method="DELETE",
        params=None
    )
    
    assert result.id == "stream_123"

# ============================================================================
# StreamRunsClient Tests
# ============================================================================

def test_list_stream_runs(runs_client, parent_mock, sample_stream_run_response):
    """Test listing stream runs."""
    mock_response = {
        "data": [sample_stream_run_response],
        "hasMore": False,
        "nextCursor": None
    }
    parent_mock.request.return_value = mock_response
    
    result = runs_client.list("stream_123")
    
    parent_mock.request.assert_called_once_with(
        "/websets/v0/streams/stream_123/runs",
        data=None,
        method="GET",
        params=None
    )
    
    assert len(result.data) == 1
    assert result.data[0].id == "run_123"
    assert result.data[0].status == "completed"
    assert result.has_more is False
    assert result.next_cursor is None

def test_get_stream_run(runs_client, parent_mock, sample_stream_run_response):
    """Test getting a specific stream run."""
    parent_mock.request.return_value = sample_stream_run_response
    
    result = runs_client.get("stream_123", "run_123")
    
    parent_mock.request.assert_called_once_with(
        "/websets/v0/streams/stream_123/runs/run_123",
        data=None,
        method="GET",
        params=None
    )
    
    assert result.id == "run_123"
    assert result.status == "completed"
    assert result.stream_id == "stream_123"

# ============================================================================
# Integration Tests
# ============================================================================

def test_streams_client_runs_integration(streams_client, parent_mock, sample_stream_run_response):
    """Test that streams client's runs attribute works correctly."""
    mock_response = {
        "data": [sample_stream_run_response],
        "hasMore": False,
        "nextCursor": None
    }
    parent_mock.request.return_value = mock_response
    
    # Access runs through the streams client
    result = streams_client.runs.list("stream_123")
    
    assert len(result.data) == 1
    assert result.data[0].id == "run_123"

def test_case_conversion_in_stream_params(streams_client, parent_mock, sample_stream_response):
    """Test that snake_case parameters are properly converted to camelCase."""
    parent_mock.request.return_value = sample_stream_response
    
    params = CreateStreamParameters(
        webset_id="ws_123",  # snake_case
        cadence=StreamCadence(cron="0 9 * * *"),  # Daily at 9:00 AM
        behavior=StreamBehaviorSearch(
            type="search",
            config=StreamBehaviorSearchConfig(
                query="test query",
                criteria=[{"description": "test"}],
                entity=WebsetCompanyEntity(type="company"),
                count=10
            )
        )
    )
    
    streams_client.create(params)
    
    # Verify the call was made with the params object
    actual_data = parent_mock.request.call_args[1]['data']
    
    # When the model is serialized, snake_case fields should become camelCase
    serialized_data = params.model_dump(by_alias=True, exclude_none=True)
    assert "websetId" in serialized_data  # Converted to camelCase
    assert "webset_id" not in serialized_data  # Original snake_case should not be present

def test_cron_expression_serialization(streams_client, parent_mock, sample_stream_response):
    """Test that cron expressions are properly serialized."""
    parent_mock.request.return_value = sample_stream_response
    
    cadence = StreamCadence(cron="0 9 * * 1", timezone="America/New_York")  # Weekly on Monday at 9:00 AM
    
    # Test cron value is preserved as string
    assert cadence.cron == "0 9 * * 1"
    assert cadence.timezone == "America/New_York"
    
    serialized = cadence.model_dump()
    assert serialized["cron"] == "0 9 * * 1"
    assert serialized["timezone"] == "America/New_York"

# ============================================================================
# Error Handling Tests
# ============================================================================

def test_streams_client_request_error_handling(streams_client, parent_mock):
    """Test that request errors are properly propagated."""
    parent_mock.request.side_effect = Exception("Network error")
    
    with pytest.raises(Exception, match="Network error"):
        streams_client.get("stream_123")

def test_invalid_stream_id_format(runs_client, parent_mock):
    """Test behavior with invalid stream ID format."""
    parent_mock.request.return_value = {"error": "Invalid stream ID"}

    # This should still make the request - validation is handled by the API
    try:
        result = runs_client.list("")
        # If no exception, the test passed (API handled it gracefully)
    except Exception:
        # Expected - the model validation will fail for error responses
        pass

    parent_mock.request.assert_called_once_with(
        "/websets/v0/streams//runs",  # Empty stream_id results in double slash
        data=None,
        method="GET",
        params=None
    ) 