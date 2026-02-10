"""
Unit tests for exa-py PR features:
- PR #160: list_all/get_all pagination helpers for monitors, imports, events
- PR #161: failed status in MonitorRunStatus enum
- PR #162: user_location parameter in async stream_answer()
- PR #163: api_base renamed to base_url + user_agent parameter in AsyncExa
- PR #164: cost_dollars field in AnswerResponse
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from exa_py import Exa, AsyncExa
from exa_py import api as exa_api
from exa_py.websets.types import MonitorRunStatus
from exa_py.websets.monitors.client import MonitorsClient, AsyncMonitorsClient
from exa_py.websets.imports.client import ImportsClient, AsyncImportsClient
from exa_py.websets.events.client import EventsClient, AsyncEventsClient


# ============================================================================
# PR #161: MonitorRunStatus.failed enum
# ============================================================================

class TestMonitorRunStatusFailedEnum:
    def test_failed_status_exists(self):
        """Test that MonitorRunStatus.failed enum value exists."""
        assert hasattr(MonitorRunStatus, 'failed')
        assert MonitorRunStatus.failed.value == 'failed'

    def test_all_expected_statuses_present(self):
        """Test that all expected statuses are present in the enum."""
        expected_statuses = ['created', 'running', 'completed', 'canceled', 'failed']
        for status in expected_statuses:
            assert hasattr(MonitorRunStatus, status), f"Missing status: {status}"

    def test_failed_status_can_be_used_in_comparison(self):
        """Test that failed status can be used in comparisons."""
        status = MonitorRunStatus.failed
        assert status == MonitorRunStatus.failed
        assert status.value == 'failed'


# ============================================================================
# PR #163: AsyncExa base_url and user_agent parameters
# ============================================================================

class TestAsyncExaConstructor:
    def test_accepts_base_url_parameter(self):
        """Test that AsyncExa accepts base_url parameter."""
        client = AsyncExa(api_key="test-key", base_url="https://custom.api.exa.ai")
        assert client.base_url == "https://custom.api.exa.ai"

    def test_default_base_url(self):
        """Test that AsyncExa uses default base_url when not specified."""
        client = AsyncExa(api_key="test-key")
        assert client.base_url == "https://api.exa.ai"

    def test_accepts_user_agent_parameter(self):
        """Test that AsyncExa accepts user_agent parameter."""
        client = AsyncExa(api_key="test-key", user_agent="custom-agent/1.0")
        assert "custom-agent/1.0" in client.headers.get("User-Agent", "")

    def test_user_agent_in_headers(self):
        """Test that user_agent is properly set in headers."""
        client = AsyncExa(api_key="test-key", user_agent="test-agent/2.0")
        user_agent = client.headers.get("User-Agent", "")
        assert "test-agent/2.0" in user_agent


# ============================================================================
# PR #164: cost_dollars field in AnswerResponse
# ============================================================================

class TestAnswerResponseCostDollars:
    def test_answer_response_has_cost_dollars_attribute(self):
        """Test that AnswerResponse has cost_dollars attribute."""
        dummy_citation = exa_api.AnswerResult(id="1", url="http://example.com", title="Test")
        response = exa_api.AnswerResponse(answer="test answer", citations=[dummy_citation])
        assert hasattr(response, 'cost_dollars')

    def test_answer_response_cost_dollars_can_be_none(self):
        """Test that cost_dollars can be None."""
        dummy_citation = exa_api.AnswerResult(id="1", url="http://example.com", title="Test")
        response = exa_api.AnswerResponse(answer="test answer", citations=[dummy_citation], cost_dollars=None)
        assert response.cost_dollars is None

    def test_answer_parses_cost_dollars_from_response(self):
        """Test that answer() method parses cost_dollars from API response."""
        exa = Exa("test-key")
        mock_response = {
            "answer": "Test answer",
            "citations": [{"id": "1", "url": "http://example.com", "title": "Test"}],
            "costDollars": {"total": 0.005}
        }
        
        with patch.object(exa, "request", return_value=mock_response):
            result = exa.answer("test query", text=False)
            assert result.cost_dollars is not None
            assert result.cost_dollars.total == 0.005

    def test_answer_handles_missing_cost_dollars(self):
        """Test that answer() handles missing costDollars gracefully."""
        exa = Exa("test-key")
        mock_response = {
            "answer": "Test answer",
            "citations": [{"id": "1", "url": "http://example.com", "title": "Test"}]
        }
        
        with patch.object(exa, "request", return_value=mock_response):
            result = exa.answer("test query", text=False)
            assert result.cost_dollars is None


# ============================================================================
# PR #162: user_location parameter in async stream_answer()
# ============================================================================

class TestAsyncStreamAnswerUserLocation:
    def test_stream_answer_has_user_location_parameter(self):
        """Test that AsyncExa.stream_answer() has user_location parameter."""
        import inspect
        client = AsyncExa(api_key="test-key")
        sig = inspect.signature(client.stream_answer)
        params = list(sig.parameters.keys())
        assert 'user_location' in params

    def test_stream_answer_signature_includes_user_location(self):
        """Test that user_location is in the method signature."""
        import inspect
        client = AsyncExa(api_key="test-key")
        sig = inspect.signature(client.stream_answer)
        param = sig.parameters.get('user_location')
        assert param is not None
        assert param.default is None


# ============================================================================
# PR #160: list_all/get_all pagination helpers
# ============================================================================

class TestMonitorsPaginationHelpers:
    @pytest.fixture
    def parent_mock(self):
        return MagicMock()

    @pytest.fixture
    def monitors_client(self, parent_mock):
        return MonitorsClient(parent_mock)

    def test_list_all_method_exists(self, monitors_client):
        """Test that monitors.list_all() method exists."""
        assert hasattr(monitors_client, 'list_all')
        assert callable(monitors_client.list_all)

    def test_get_all_method_exists(self, monitors_client):
        """Test that monitors.get_all() method exists."""
        assert hasattr(monitors_client, 'get_all')
        assert callable(monitors_client.get_all)

    def test_list_all_has_correct_signature(self, monitors_client):
        """Test that list_all() has the expected parameters."""
        import inspect
        sig = inspect.signature(monitors_client.list_all)
        params = list(sig.parameters.keys())
        assert 'limit' in params
        assert 'webset_id' in params

    def test_get_all_has_correct_signature(self, monitors_client):
        """Test that get_all() has the expected parameters."""
        import inspect
        sig = inspect.signature(monitors_client.get_all)
        params = list(sig.parameters.keys())
        assert 'limit' in params
        assert 'webset_id' in params


class TestImportsPaginationHelpers:
    @pytest.fixture
    def parent_mock(self):
        return MagicMock()

    @pytest.fixture
    def imports_client(self, parent_mock):
        return ImportsClient(parent_mock)

    def test_list_all_method_exists(self, imports_client):
        """Test that imports.list_all() method exists."""
        assert hasattr(imports_client, 'list_all')
        assert callable(imports_client.list_all)

    def test_get_all_method_exists(self, imports_client):
        """Test that imports.get_all() method exists."""
        assert hasattr(imports_client, 'get_all')
        assert callable(imports_client.get_all)

    def test_list_all_has_correct_signature(self, imports_client):
        """Test that list_all() has the expected parameters."""
        import inspect
        sig = inspect.signature(imports_client.list_all)
        params = list(sig.parameters.keys())
        assert 'limit' in params

    def test_get_all_has_correct_signature(self, imports_client):
        """Test that get_all() has the expected parameters."""
        import inspect
        sig = inspect.signature(imports_client.get_all)
        params = list(sig.parameters.keys())
        assert 'limit' in params


class TestEventsPaginationHelpers:
    @pytest.fixture
    def parent_mock(self):
        return MagicMock()

    @pytest.fixture
    def events_client(self, parent_mock):
        return EventsClient(parent_mock)

    def test_list_all_method_exists(self, events_client):
        """Test that events.list_all() method exists."""
        assert hasattr(events_client, 'list_all')
        assert callable(events_client.list_all)

    def test_get_all_method_exists(self, events_client):
        """Test that events.get_all() method exists."""
        assert hasattr(events_client, 'get_all')
        assert callable(events_client.get_all)

    def test_list_all_has_correct_signature(self, events_client):
        """Test that list_all() has the expected parameters."""
        import inspect
        sig = inspect.signature(events_client.list_all)
        params = list(sig.parameters.keys())
        assert 'limit' in params

    def test_get_all_has_correct_signature(self, events_client):
        """Test that get_all() has the expected parameters."""
        import inspect
        sig = inspect.signature(events_client.get_all)
        params = list(sig.parameters.keys())
        assert 'limit' in params


# ============================================================================
# PR #160: Async pagination helpers
# ============================================================================

class TestAsyncMonitorsPaginationHelpers:
    @pytest.fixture
    def parent_mock(self):
        mock = MagicMock()
        mock.async_request = AsyncMock()
        return mock

    @pytest.fixture
    def async_monitors_client(self, parent_mock):
        return AsyncMonitorsClient(parent_mock)

    def test_async_list_all_method_exists(self, async_monitors_client):
        """Test that async monitors.list_all() method exists."""
        assert hasattr(async_monitors_client, 'list_all')

    def test_async_get_all_method_exists(self, async_monitors_client):
        """Test that async monitors.get_all() method exists."""
        assert hasattr(async_monitors_client, 'get_all')


class TestAsyncImportsPaginationHelpers:
    @pytest.fixture
    def parent_mock(self):
        mock = MagicMock()
        mock.async_request = AsyncMock()
        return mock

    @pytest.fixture
    def async_imports_client(self, parent_mock):
        return AsyncImportsClient(parent_mock)

    def test_async_list_all_method_exists(self, async_imports_client):
        """Test that async imports.list_all() method exists."""
        assert hasattr(async_imports_client, 'list_all')

    def test_async_get_all_method_exists(self, async_imports_client):
        """Test that async imports.get_all() method exists."""
        assert hasattr(async_imports_client, 'get_all')


class TestAsyncEventsPaginationHelpers:
    @pytest.fixture
    def parent_mock(self):
        mock = MagicMock()
        mock.async_request = AsyncMock()
        return mock

    @pytest.fixture
    def async_events_client(self, parent_mock):
        return AsyncEventsClient(parent_mock)

    def test_async_list_all_method_exists(self, async_events_client):
        """Test that async events.list_all() method exists."""
        assert hasattr(async_events_client, 'list_all')

    def test_async_get_all_method_exists(self, async_events_client):
        """Test that async events.get_all() method exists."""
        assert hasattr(async_events_client, 'get_all')
