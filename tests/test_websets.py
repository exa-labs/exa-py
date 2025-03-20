from datetime import datetime
import json
from typing import Dict, Any

from pydantic import AnyUrl
import pytest
from unittest.mock import MagicMock

from exa_py.websets.client import WebsetsClient
from exa_py.websets.core.base import WebsetsBaseClient
from exa_py.api import snake_to_camel, camel_to_snake, to_camel_case, to_snake_case
from exa_py.websets.core.model import (
    UpdateWebsetRequest,
    CreateWebsetRequest,
    Search
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
def base_client(parent_mock):
    """Create a base client instance with mock parent."""
    return WebsetsBaseClient(parent_mock)

@pytest.fixture
def websets_client(parent_mock):
    """Create a WebsetsClient instance with mock parent."""
    return WebsetsClient(parent_mock)

@pytest.fixture
def items_client(websets_client):
    """Create an items client instance."""
    return websets_client.items

# ============================================================================
# Case Conversion Tests
# ============================================================================

@pytest.mark.parametrize("input,expected", [
    ("test_case", "testCase"),
    ("multiple_word_test", "multipleWordTest"),
    ("single", "single"),
    ("schema_", "$schema"),  # Special case
    ("not_", "not"),  # Special case
])
def test_snake_to_camel(input, expected):
    """Test snake_case to camelCase conversion."""
    assert snake_to_camel(input) == expected

@pytest.mark.parametrize("input,expected", [
    ("testCase", "test_case"),
    ("multipleWordTest", "multiple_word_test"),
    ("single", "single"),
])
def test_camel_to_snake(input, expected):
    """Test camelCase to snake_case conversion."""
    assert camel_to_snake(input) == expected

def test_dict_to_camel_case():
    """Test converting dictionary keys from snake_case to camelCase."""
    snake_dict = {
        "test_key": "value",
        "nested_dict": {
            "inner_key": 123,
            "another_key": True
        },
        "normal_key": None
    }
    
    expected = {
        "testKey": "value",
        "nestedDict": {
            "innerKey": 123,
            "anotherKey": True
        }
    }
    
    assert to_camel_case(snake_dict) == expected

def test_dict_to_snake_case():
    """Test converting dictionary keys from camelCase to snake_case."""
    camel_dict = {
        "testKey": "value",
        "nestedDict": {
            "innerKey": 123,
            "anotherKey": True
        }
    }
    
    expected = {
        "test_key": "value",
        "nested_dict": {
            "inner_key": 123,
            "another_key": True
        }
    }
    
    assert to_snake_case(camel_dict) == expected

def test_request_body_case_conversion(websets_client, parent_mock):
    """Test that request body fields are converted from snake_case to camelCase."""
    mock_response = {
        "id": "ws_123",
        "object": "webset",
        "status": "idle",
        "externalId": "test-id",
        "createdAt": "2023-01-01T00:00:00Z",
        "updatedAt": "2023-01-01T00:00:00Z",
        "searches": [],
        "enrichments": []
    }
    
    parent_mock.request.return_value = mock_response
    
    # Create a request with snake_case fields
    request = CreateWebsetRequest(
        external_id="test-id",  # This will be sent as externalId to the API
        search=Search(
            query="test query",
            count=10
        ),
        metadata={"snake_case_key": "value"}  # This should remain unchanged
    )
    
    result = websets_client.create(params=request)
    
    # Verify the request body was converted to camelCase
    actual_data = parent_mock.request.call_args[1]['data']
    assert actual_data == {
        "search": {
            "query": "test query",
            "count": 10
        },
        "externalId": "test-id",  # This should be camelCase in the request
        "metadata": {"snake_case_key": "value"}  # metadata preserved original case
    }

def test_response_case_conversion(websets_client, parent_mock):
    """Test that API response fields are converted from camelCase to snake_case."""
    mock_response = {
        "id": "ws_123",
        "object": "webset",
        "status": "idle",
        "externalId": "test-id",
        "createdAt": "2023-01-01T00:00:00Z",
        "updatedAt": "2023-01-01T00:00:00Z",
        "searches": [],
        "enrichments": []
    }
    
    parent_mock.request.return_value = mock_response
    result = websets_client.retrieve(id="ws_123")
    
    # Test that API camelCase is converted to SDK snake_case
    assert result.external_id == "test-id"
    assert result.created_at == datetime.fromisoformat(mock_response["createdAt"])


def test_metadata_case_preservation(websets_client, parent_mock):
    """Test that metadata keys preserve their original case format when sent to API."""
    # Test case preservation in both directions
    test_cases = [
        {"snake_case_key": "value"},  # Snake case should be preserved
        {"camelCaseKey": "value"},    # Camel case should be preserved
        {"UPPER_CASE": "value"},      # Upper case should be preserved
        {"mixed_Case_Key": "value"},  # Mixed case should be preserved
    ]
    
    for metadata in test_cases:
        mock_response = {
            "id": "ws_123",
            "object": "webset",
            "status": "idle",
            "metadata": metadata,
            "externalId": "test-id",
            "searches": [],
            "enrichments": [],
            "createdAt": "2023-01-01T00:00:00Z",
            "updatedAt": "2023-01-01T00:00:00Z"
        }
        
        parent_mock.request.return_value = mock_response
        
        # Test sending metadata to API
        request = UpdateWebsetRequest(metadata=metadata)
        result = websets_client.update(id="ws_123", params=request)
        
        # Verify metadata case is preserved in request
        actual_data = parent_mock.request.call_args[1]['data']
        assert actual_data["metadata"] == metadata
        
        # Verify metadata case is preserved in response
        assert result.metadata == metadata

def test_nested_property_case_conversion(items_client, parent_mock):
    """Test that nested property fields follow proper case conversion rules."""
    mock_response = {
        "data": [{
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
        }],
        "hasMore": False,
        "nextCursor": None
    }
    
    parent_mock.request.return_value = mock_response
    result = items_client.list(webset_id="ws_123", limit=10)
    
    assert result.data[0].properties.company.logo_url == AnyUrl("https://example.com/logo.png")

def test_request_forwards_to_parent(base_client, parent_mock):
    """Test that BaseClient.request forwards to the parent client's request method."""
    parent_mock.request.return_value = {"key": "value"}
    
    result = base_client.request(
        "/test", 
        data={"param": "value"}, 
        method="POST",
        params={"query": "test"}
    )
    
    parent_mock.request.assert_called_once_with(
        "/test", 
        data={"param": "value"}, 
        method="POST",
        params={"query": "test"}
    )
    assert result == {"key": "value"} 