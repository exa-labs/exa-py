from datetime import datetime
import json
from typing import Dict, Any

import pytest
from unittest.mock import MagicMock

from exa_py.websets.monitors.client import MonitorsClient
from exa_py.websets.monitors.runs.client import MonitorRunsClient
from exa_py.websets.types import (
    CreateMonitorParameters,
    UpdateMonitor,
    MonitorBehaviorSearch,
    MonitorBehaviorRefresh,
    MonitorBehaviorSearchConfig,
    MonitorRefreshBehaviorEnrichmentsConfig,
    MonitorRefreshBehaviorContentsConfig,
    MonitorCadence,
    MonitorStatus,
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
def monitors_client(parent_mock):
    """Create a MonitorsClient instance with mock parent."""
    return MonitorsClient(parent_mock)

@pytest.fixture
def runs_client(parent_mock):
    """Create a MonitorRunsClient instance with mock parent."""
    return MonitorRunsClient(parent_mock)

@pytest.fixture
def sample_monitor_response():
    """Sample monitor response data."""
    return {
        "id": "monitor_123",
        "object": "monitor",
        "status": "enabled",
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
            "object": "monitor_run",
            "status": "completed",
            "monitorId": "monitor_123",
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
def sample_monitor_run_response():
    """Sample monitor run response data."""
    return {
        "id": "run_123",
        "object": "monitor_run",
        "status": "completed",
        "monitorId": "monitor_123",
        "type": "search",
        "completedAt": "2023-01-01T10:00:00Z",
        "failedAt": None,
        "canceledAt": None,
        "createdAt": "2023-01-01T09:00:00Z",
        "updatedAt": "2023-01-01T10:00:00Z"
    }

# ============================================================================
# MonitorsClient Tests
# ============================================================================

def test_monitors_client_has_runs_client(monitors_client):
    """Test that MonitorsClient properly initializes with a runs client."""
    assert hasattr(monitors_client, 'runs')
    assert isinstance(monitors_client.runs, MonitorRunsClient)

def test_create_monitor_with_search_behavior(monitors_client, parent_mock, sample_monitor_response):
    """Test creating a monitor with search behavior."""
    parent_mock.request.return_value = sample_monitor_response
    
    # Create parameters with search behavior
    params = CreateMonitorParameters(
        webset_id="ws_123",
        cadence=MonitorCadence(
            cron="0 9 * * *",  # Daily at 9:00 AM
            timezone="America/New_York"
        ),
        behavior=MonitorBehaviorSearch(
            type="search",
            config=MonitorBehaviorSearchConfig(
                query="AI startups",
                criteria=[{"description": "Must be AI focused"}],
                entity=WebsetCompanyEntity(type="company"),
                count=10
            )
        ),
        metadata={"environment": "test"}
    )
    
    result = monitors_client.create(params)
    
    # Verify the request was made correctly
    parent_mock.request.assert_called_once_with(
        "/websets/v0/monitors",
        data={
            'websetId': 'ws_123',
            'cadence': {'cron': '0 9 * * *', 'timezone': 'America/New_York'},
            'behavior': {
                'type': 'search',
                'config': {
                    'query': 'AI startups',
                    'criteria': [{'description': 'Must be AI focused'}],
                    'entity': {'type': 'company'},
                    'count': 10,
                    'behavior': 'append'
                }
            },
            'metadata': {'environment': 'test'}
        },
        method="POST",
        params=None
    )
    
    # Verify the response
    assert result.id == "monitor_123"
    assert result.webset_id == "ws_123"
    assert result.status == "enabled"

def test_create_monitor_with_refresh_behavior(monitors_client, parent_mock, sample_monitor_response):
    """Test creating a monitor with refresh behavior."""
    # Modify response for refresh behavior
    refresh_response = sample_monitor_response.copy()
    refresh_response["behavior"] = {
        "type": "refresh",
        "config": {
            "target": "enrichments",
            "enrichments": {"ids": ["enrich_123"]}
        }
    }
    parent_mock.request.return_value = refresh_response
    
    params = CreateMonitorParameters(
        webset_id="ws_123",
        cadence=MonitorCadence(cron="0 9 * * 1"),  # Weekly on Monday at 9:00 AM
        behavior=MonitorBehaviorRefresh(
            type="refresh",
            config=MonitorRefreshBehaviorEnrichmentsConfig(
                target="enrichments",
                enrichments={"ids": ["enrich_123"]}
            )
        )
    )
    
    result = monitors_client.create(params)
    
    assert result.id == "monitor_123"
    assert result.behavior.type == "refresh"

def test_create_monitor_with_contents_refresh(monitors_client, parent_mock, sample_monitor_response):
    """Test creating a monitor with contents refresh behavior."""
    # Modify response for contents refresh
    refresh_response = sample_monitor_response.copy()
    refresh_response["behavior"] = {
        "type": "refresh",
        "config": {
            "target": "contents"
        }
    }
    parent_mock.request.return_value = refresh_response
    
    params = CreateMonitorParameters(
        webset_id="ws_123",
        cadence=MonitorCadence(cron="0 9 * * 1"),
        behavior=MonitorBehaviorRefresh(
            type="refresh",
            config=MonitorRefreshBehaviorContentsConfig(target="contents")
        )
    )
    
    result = monitors_client.create(params)
    
    assert result.id == "monitor_123"
    assert result.behavior.type == "refresh"
    assert result.behavior.config.target == "contents"

def test_create_monitor_with_dict_params(monitors_client, parent_mock, sample_monitor_response):
    """Test creating a monitor with dictionary parameters."""
    parent_mock.request.return_value = sample_monitor_response
    
    params = {
        "websetId": "ws_123",
        "cadence": {
            "cron": "0 9 * * *",
            "timezone": "America/New_York"
        },
        "behavior": {
            "type": "search",
            "config": {
                "query": "AI startups",
                "criteria": [{"description": "Must be AI focused"}],
                "entity": {"type": "company"},
                "count": 10
            }
        }
    }
    
    result = monitors_client.create(params)
    
    assert result.id == "monitor_123"
    assert result.webset_id == "ws_123"

def test_get_monitor(monitors_client, parent_mock, sample_monitor_response):
    """Test getting a specific monitor."""
    parent_mock.request.return_value = sample_monitor_response
    
    result = monitors_client.get("monitor_123")
    
    parent_mock.request.assert_called_once_with(
        "/websets/v0/monitors/monitor_123",
        data=None,
        method="GET",
        params=None
    )
    
    assert result.id == "monitor_123"
    assert result.status == "enabled"

def test_list_monitors(monitors_client, parent_mock):
    """Test listing monitors with parameters."""
    response_data = {
        "data": [
            {
                "id": "monitor_123",
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
                        "behavior": "append"
                    }
                },
                "metadata": {},
                "createdAt": "2023-01-01T00:00:00Z",
                "updatedAt": "2023-01-01T00:00:00Z"
            }
        ],
        "hasMore": False,
        "nextCursor": None
    }
    parent_mock.request.return_value = response_data
    
    result = monitors_client.list(cursor="cursor_123", limit=10, webset_id="ws_123")
    
    parent_mock.request.assert_called_once_with(
        "/websets/v0/monitors",
        data=None,
        method="GET",
        params={"cursor": "cursor_123", "limit": 10, "websetId": "ws_123"}
    )
    
    assert len(result.data) == 1
    assert result.data[0].id == "monitor_123"
    assert not result.has_more

def test_list_monitors_no_params(monitors_client, parent_mock):
    """Test listing monitors without parameters."""
    response_data = {
        "data": [],
        "hasMore": False,
        "nextCursor": None
    }
    parent_mock.request.return_value = response_data
    
    result = monitors_client.list()
    
    parent_mock.request.assert_called_once_with(
        "/websets/v0/monitors",
        data=None,
        method="GET",
        params={}
    )
    
    assert len(result.data) == 0

def test_update_monitor(monitors_client, parent_mock, sample_monitor_response):
    """Test updating a monitor."""
    updated_response = sample_monitor_response.copy()
    updated_response["status"] = "disabled"
    parent_mock.request.return_value = updated_response
    
    params = UpdateMonitor(status=MonitorStatus.disabled, metadata={"updated": "true"})
    
    result = monitors_client.update("monitor_123", params)
    
    parent_mock.request.assert_called_once_with(
        "/websets/v0/monitors/monitor_123",
        data={"status": "disabled", "metadata": {"updated": "true"}},
        method="PATCH",
        params=None
    )
    
    assert result.id == "monitor_123"
    assert result.status == "disabled"

def test_update_monitor_with_dict(monitors_client, parent_mock, sample_monitor_response):
    """Test updating a monitor with dictionary parameters."""
    updated_response = sample_monitor_response.copy()
    updated_response["status"] = "disabled"
    parent_mock.request.return_value = updated_response
    
    params = {"status": "disabled", "metadata": {"updated": "true"}}
    
    result = monitors_client.update("monitor_123", params)
    
    assert result.id == "monitor_123"
    assert result.status == "disabled"

def test_delete_monitor(monitors_client, parent_mock, sample_monitor_response):
    """Test deleting a monitor."""
    deleted_response = sample_monitor_response.copy()
    deleted_response["status"] = "disabled"
    parent_mock.request.return_value = deleted_response
    
    result = monitors_client.delete("monitor_123")
    
    parent_mock.request.assert_called_once_with(
        "/websets/v0/monitors/monitor_123",
        data=None,
        method="DELETE",
        params=None
    )
    
    assert result.id == "monitor_123"

# ============================================================================
# MonitorRunsClient Tests
# ============================================================================

def test_list_monitor_runs(runs_client, parent_mock, sample_monitor_run_response):
    """Test listing monitor runs."""
    response_data = {
        "data": [sample_monitor_run_response],
        "hasMore": False,
        "nextCursor": None
    }
    parent_mock.request.return_value = response_data
    
    result = runs_client.list("monitor_123")
    
    parent_mock.request.assert_called_once_with(
        "/websets/v0/monitors/monitor_123/runs",
        data=None,
        method="GET",
        params=None
    )
    
    assert len(result.data) == 1
    assert result.data[0].id == "run_123"
    assert result.data[0].monitor_id == "monitor_123"

def test_get_monitor_run(runs_client, parent_mock, sample_monitor_run_response):
    """Test getting a specific monitor run."""
    parent_mock.request.return_value = sample_monitor_run_response
    
    result = runs_client.get("monitor_123", "run_123")
    
    parent_mock.request.assert_called_once_with(
        "/websets/v0/monitors/monitor_123/runs/run_123",
        data=None,
        method="GET",
        params=None
    )
    
    assert result.id == "run_123"
    assert result.monitor_id == "monitor_123"
    assert result.status == "completed"

def test_monitors_client_runs_integration(monitors_client, parent_mock, sample_monitor_run_response):
    """Test that monitors client properly integrates with runs client."""
    response_data = {
        "data": [sample_monitor_run_response],
        "hasMore": False,
        "nextCursor": None
    }
    parent_mock.request.return_value = response_data
    
    result = monitors_client.runs.list("monitor_123")
    
    assert len(result.data) == 1
    assert result.data[0].id == "run_123"

def test_case_conversion_in_monitor_params(monitors_client, parent_mock, sample_monitor_response):
    """Test that camelCase fields are properly handled."""
    parent_mock.request.return_value = sample_monitor_response
    
    params = CreateMonitorParameters(
        webset_id="ws_123",  # This should become websetId
        cadence=MonitorCadence(cron="0 9 * * *"),
        behavior=MonitorBehaviorSearch(
            type="search",
            config=MonitorBehaviorSearchConfig(
                query="test",
                criteria=[],
                entity=WebsetCompanyEntity(type="company"),
                count=10
            )
        )
    )
    
    result = monitors_client.create(params)
    
    # Verify the response properly maps camelCase back to snake_case
    assert result.webset_id == "ws_123"  # websetId -> webset_id
    assert result.next_run_at is not None  # nextRunAt -> next_run_at

def test_cron_expression_serialization(monitors_client, parent_mock, sample_monitor_response):
    """Test that cron expressions are properly serialized."""
    parent_mock.request.return_value = sample_monitor_response
    
    params = CreateMonitorParameters(
        webset_id="ws_123",
        cadence=MonitorCadence(
            cron="0 9 * * 1-5",  # Weekdays at 9 AM
            timezone="America/New_York"
        ),
        behavior=MonitorBehaviorSearch(
            type="search",
            config=MonitorBehaviorSearchConfig(
                query="test",
                criteria=[],
                entity=WebsetCompanyEntity(type="company"),
                count=5
            )
        )
    )
    
    result = monitors_client.create(params)
    
    assert result.cadence.cron == "0 9 * * *"  # From response
    assert result.cadence.timezone == "Etc/UTC"  # From response

def test_monitors_client_request_error_handling(monitors_client, parent_mock):
    """Test that client properly handles request errors."""
    parent_mock.request.side_effect = Exception("Network error")
    
    with pytest.raises(Exception, match="Network error"):
        monitors_client.get("monitor_123")

def test_invalid_monitor_id_format(runs_client, parent_mock):
    """Test handling of invalid monitor ID format."""
    parent_mock.request.side_effect = Exception("Invalid monitor ID")
    
    with pytest.raises(Exception, match="Invalid monitor ID"):
        runs_client.list("invalid_id") 