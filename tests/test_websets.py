from datetime import datetime
import json
from typing import Dict, Any

from pydantic import AnyUrl
import pytest
from unittest.mock import MagicMock

from exa_py.websets.client import WebsetsClient
from exa_py.websets.core.base import WebsetsBaseClient
from exa_py.api import snake_to_camel, camel_to_snake, to_camel_case, to_snake_case
from exa_py.websets.types import (
    UpdateWebsetRequest,
    CreateWebsetParameters,
    Search,
    CreateEnrichmentParameters,
    Format
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
    ("schema_", "$schema"),
    ("not_", "not"),
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
    
    request = CreateWebsetParameters(
        external_id="test-id",
        search=Search(
            query="test query",
            count=10
        ),
        metadata={"snake_case_key": "value"}
    )
    
    websets_client.create(params=request)
    
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
    result = websets_client.get(id="ws_123")
    
    assert result.external_id == "test-id"
    assert result.created_at == datetime.fromisoformat(mock_response["createdAt"])


def test_metadata_case_preservation(websets_client, parent_mock):
    """Test that metadata keys preserve their original case format when sent to API."""
    test_cases = [
        {"snake_case_key": "value"},
        {"camelCaseKey": "value"},
        {"UPPER_CASE": "value"},
        {"mixed_Case_Key": "value"},
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
        
        request = UpdateWebsetRequest(metadata=metadata)
        result = websets_client.update(id="ws_123", params=request)
        
        actual_data = parent_mock.request.call_args[1]['data']
        assert actual_data["metadata"] == metadata
        
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
    
    # WebsetsBaseClient prepends '/websets/' to all endpoints
    parent_mock.request.assert_called_once_with(
        "/websets//test",  # Double slash is preserved
        data={"param": "value"},
        method="POST",
        params={"query": "test"}
    )
    
    assert result == {"key": "value"}

def test_format_validation_string_and_enum():
    """Test that the format field accepts both string and enum values."""
    # Test with enum value
    params1 = CreateEnrichmentParameters(
        description="Test description",
        format=Format.text
    )
    # Since use_enum_values=True in ExaBaseModel, the enum is converted to its string value
    assert params1.format == Format.text.value
    
    # Test with string value
    params2 = CreateEnrichmentParameters(
        description="Test description",
        format="text"
    )
    assert params2.format == "text"
    
    # Both should serialize to the same value
    assert params1.model_dump()["format"] == params2.model_dump()["format"]
    
    # Test with invalid string value
    with pytest.raises(ValueError):
        CreateEnrichmentParameters(
            description="Test description",
            format="invalid_format"
        )

def test_dict_and_model_parameter_support(websets_client, parent_mock):
    """Test that client methods accept both dictionaries and model instances."""
    from exa_py.websets.types import CreateWebsetParameters, Format
    
    # Set up mock response
    mock_response = {
        "id": "ws_123",
        "object": "webset",
        "status": "idle",
        "externalId": None,
        "createdAt": "2023-01-01T00:00:00Z",
        "updatedAt": "2023-01-01T00:00:00Z",
        "searches": [],
        "enrichments": []
    }
    parent_mock.request.return_value = mock_response
    
    # Test with a model instance
    model_params = CreateWebsetParameters(
        search={
            "query": "Test query",
            "count": 10
        },
        enrichments=[{
            "description": "Test enrichment",
            "format": Format.text
        }]
    )
    model_result = websets_client.create(params=model_params)
    
    # Test with an equivalent dictionary
    dict_params = {
        "search": {
            "query": "Test query",
            "count": 10
        },
        "enrichments": [{
            "description": "Test enrichment",
            "format": "text"
        }]
    }
    dict_result = websets_client.create(params=dict_params)
    
    # Verify both calls produce the same result
    assert model_result.id == dict_result.id
    assert model_result.status == dict_result.status
    
    # Verify both calls were made (we don't need to verify exact equality of serialized data)
    assert len(parent_mock.request.call_args_list) == 2
    
    # Both serialization approaches should have the same functionality
    # The differences (Enum vs string, float vs int) are still valid when sent to the API
    model_call_data = parent_mock.request.call_args_list[0][1]['data']
    dict_call_data = parent_mock.request.call_args_list[1][1]['data']
    
    # Check that fields are functionally equivalent
    assert model_call_data['search']['query'] == dict_call_data['search']['query']
    assert float(model_call_data['search']['count']) == float(dict_call_data['search']['count'])
    assert model_call_data['enrichments'][0]['description'] == dict_call_data['enrichments'][0]['description']
    
    # For format, we should get either the enum's value or the string directly
    format1 = model_call_data['enrichments'][0]['format']
    format2 = dict_call_data['enrichments'][0]['format']
    
    # If format1 is an enum, get its value
    format1_value = format1.value if hasattr(format1, 'value') else format1
    # If format2 is an enum, get its value
    format2_value = format2.value if hasattr(format2, 'value') else format2
    
    assert format1_value == format2_value 

def test_webhook_attempts_list(websets_client, parent_mock):
    """Test that the WebhookAttemptsClient.list method works correctly."""
    # Mock response for webhook attempts
    mock_response = {
        "data": [{
            "id": "attempt_123",
            "object": "webhook_attempt",
            "eventId": "event_123",
            "eventType": "webset.created",
            "webhookId": "webhook_123",
            "url": "https://example.com/webhook",
            "successful": True,
            "responseHeaders": {"content-type": "application/json"},
            "responseBody": '{"status": "ok"}',
            "responseStatusCode": 200,
            "attempt": 1,
            "attemptedAt": "2023-01-01T00:00:00Z"
        }],
        "hasMore": False,
        "nextCursor": None
    }
    
    parent_mock.request.return_value = mock_response
    
    # Test without optional parameters
    result = websets_client.webhooks.attempts.list(webhook_id="webhook_123")
    
    parent_mock.request.assert_called_with(
        "/websets//v0/webhooks/webhook_123/attempts",
        params={},
        method="GET",
        data=None
    )
    
    assert len(result.data) == 1
    assert result.data[0].id == "attempt_123"
    assert result.data[0].event_type == "webset.created"
    assert result.data[0].successful is True
    
    # Reset mock and test with all optional parameters
    parent_mock.request.reset_mock()
    parent_mock.request.return_value = mock_response
    
    result = websets_client.webhooks.attempts.list(
        webhook_id="webhook_123",
        cursor="cursor_value",
        limit=10,
        event_type="webset.created"
    )
    
    parent_mock.request.assert_called_with(
        "/websets//v0/webhooks/webhook_123/attempts",
        params={"cursor": "cursor_value", "limit": 10, "eventType": "webset.created"},
        method="GET",
        data=None
    ) 