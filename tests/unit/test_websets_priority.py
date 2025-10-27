"""
Tests for Websets priority header functionality.
"""

import pytest
from unittest.mock import patch
from exa_py import Exa
from exa_py.websets.types import WebsetSearchBehavior, RequestOptions


@pytest.fixture
def mock_exa():
    """Create a mock Exa client."""
    exa = Exa(api_key="test_api_key")
    return exa


def test_webset_create_with_priority_option(mock_exa):
    """Test that priority option is converted to the correct header."""
    
    # Mock the request method
    with patch.object(mock_exa, 'request') as mock_request:
        mock_request.return_value = {
            "id": "test_webset_id",
            "object": "webset",
            "status": "running",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "searches": [],
            "enrichments": [],
            "monitors": [],
        }
        
        # Create webset with low priority using simplified API
        mock_exa.websets.create(
            {
                "search": {
                    "query": "test query",
                    "count": 10,
                },
            },
            options={"priority": "low"}  # Simplified priority option
        )
        
        # Verify request was called with correct headers
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert "headers" in call_args.kwargs
        assert call_args.kwargs["headers"]["x-exa-websets-priority"] == "low"


def test_webset_create_with_request_options(mock_exa):
    """Test that RequestOptions object with priority is handled correctly."""
    
    # Mock the request method
    with patch.object(mock_exa, 'request') as mock_request:
        mock_request.return_value = {
            "id": "test_webset_id",
            "object": "webset",
            "status": "running",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "searches": [],
            "enrichments": [],
            "monitors": [],
        }
        
        # Create webset with RequestOptions using priority field
        options = RequestOptions(priority="high")
        mock_exa.websets.create(
            {
                "search": {
                    "query": "test query",
                    "count": 10,
                },
            },
            options=options
        )
        
        # Verify request was called with correct headers
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert "headers" in call_args.kwargs
        assert call_args.kwargs["headers"]["x-exa-websets-priority"] == "high"


def test_priority_with_additional_headers(mock_exa):
    """Test that priority option works alongside custom headers."""
    
    # Mock the request method
    with patch.object(mock_exa, 'request') as mock_request:
        mock_request.return_value = {
            "id": "test_webset_id",
            "object": "webset",
            "status": "idle",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "searches": [],
            "enrichments": [],
            "monitors": [],
        }
        
        # Create webset with both priority and custom headers
        mock_exa.websets.create(
            {
                "search": {
                    "query": "test query",
                    "count": 10,
                },
            },
            options={
                "priority": "medium",
                "headers": {"x-custom-header": "custom-value"}
            }
        )
        
        # Verify request was called with both headers
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert "headers" in call_args.kwargs
        assert call_args.kwargs["headers"]["x-exa-websets-priority"] == "medium"
        assert call_args.kwargs["headers"]["x-custom-header"] == "custom-value"


def test_search_create_with_priority_option(mock_exa):
    """Test that priority option is converted to the correct header for searches."""
    
    # Mock the request method
    with patch.object(mock_exa, 'request') as mock_request:
        mock_request.return_value = {
            "id": "test_search_id",
            "object": "webset_search",
            "webset_id": "test_webset_id",
            "status": "running",
            "query": "test search query",
            "criteria": [],
            "count": 5,
            "progress": {
                "found": 0,
                "total": 5,
                "completion": 0.0
            },
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }
        
        # Create search with medium priority using simplified API
        mock_exa.websets.searches.create(
            "test_webset_id",
            {
                "query": "test search query",
                "count": 5,
                "behavior": WebsetSearchBehavior.override.value,
            },
            options={"priority": "medium"}  # Simplified priority option
        )
        
        # Verify request was called with correct headers
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert "headers" in call_args.kwargs
        assert call_args.kwargs["headers"]["x-exa-websets-priority"] == "medium"


def test_backward_compatibility_with_headers(mock_exa):
    """Test that the old method of passing headers still works for backward compatibility."""
    
    # Mock the request method
    with patch.object(mock_exa, 'request') as mock_request:
        mock_request.return_value = {
            "id": "test_webset_id",
            "object": "webset",
            "status": "idle",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "searches": [],
            "enrichments": [],
            "monitors": [],
        }
        
        # Create webset using old method with headers directly
        mock_exa.websets.create(
            {
                "search": {
                    "query": "test query",
                    "count": 10,
                },
            },
            options={
                "headers": {
                    "x-exa-websets-priority": "high",
                    "x-custom-header": "custom-value"
                }
            }
        )
        
        # Verify request was called with all headers
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert "headers" in call_args.kwargs
        assert call_args.kwargs["headers"]["x-exa-websets-priority"] == "high"
        assert call_args.kwargs["headers"]["x-custom-header"] == "custom-value"


def test_no_options_still_works(mock_exa):
    """Test that requests without options still work."""
    
    # Mock the request method
    with patch.object(mock_exa, 'request') as mock_request:
        mock_request.return_value = {
            "id": "test_webset_id",
            "object": "webset",
            "status": "paused",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "searches": [],
            "enrichments": [],
            "monitors": [],
        }
        
        # Create webset without options
        mock_exa.websets.create(
            {
                "search": {
                    "query": "test query",
                    "count": 10,
                },
            }
        )
        
        # Verify request was called without additional headers
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        # headers may be None or not present in kwargs
        if "headers" in call_args.kwargs:
            assert call_args.kwargs["headers"] is None


def test_priority_values():
    """Test that all priority values are valid."""
    from exa_py.websets.types import WebsetPriority
    
    assert WebsetPriority.low.value == "low"
    assert WebsetPriority.medium.value == "medium"
    assert WebsetPriority.high.value == "high"
    
    # Ensure all expected values are present
    priority_values = [p.value for p in WebsetPriority]
    assert "low" in priority_values
    assert "medium" in priority_values
    assert "high" in priority_values
    assert len(priority_values) == 3
