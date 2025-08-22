import asyncio
from datetime import datetime
import json
from typing import Dict, Any
from unittest.mock import MagicMock, AsyncMock

from pydantic import AnyUrl
import pytest

from exa_py.websets.client import WebsetsClient, AsyncWebsetsClient
from exa_py.websets.core.base import WebsetsBaseClient
from exa_py.websets.core.async_base import WebsetsAsyncBaseClient
from exa_py.api import snake_to_camel, camel_to_snake, to_camel_case, to_snake_case
from exa_py.websets.types import (
    UpdateWebsetRequest,
    CreateWebsetParameters,
    CreateWebsetParametersSearch,
    CreateEnrichmentParameters,
    Format,
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
# Async Fixtures
# ============================================================================

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
        "enrichments": [],
        "monitors": []
    }
    
    parent_mock.request.return_value = mock_response
    
    request = CreateWebsetParameters(
        external_id="test-id",
        search=CreateWebsetParametersSearch(
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
        "enrichments": [],
        "monitors": []
    }
    
    parent_mock.request.return_value = mock_response
    result = websets_client.get(id="ws_123")
    
    assert result.external_id == "test-id"
    assert result.created_at == datetime.fromisoformat(mock_response["createdAt"].replace('Z', '+00:00'))


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
            "monitors": [],
            "createdAt": "2023-01-01T00:00:00Z",
            "updatedAt": "2023-01-01T00:00:00Z"
        }
        
        parent_mock.request.return_value = mock_response
        
        request = UpdateWebsetRequest(metadata=metadata)
        result = websets_client.update(id="ws_123", params=request)
        
        assert result.metadata == metadata
        
        actual_data = parent_mock.request.call_args[1]['data']
        assert actual_data["metadata"] == metadata

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
        "/websets/test",
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
        "enrichments": [],
        "monitors": []
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
        "/websets/v0/webhooks/webhook_123/attempts",
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
        "/websets/v0/webhooks/webhook_123/attempts",
        params={"cursor": "cursor_value", "limit": 10, "eventType": "webset.created"},
        method="GET",
        data=None
    )


def test_preview_webset(websets_client, parent_mock):
    """Test webset preview method."""
    mock_response = {
        "search": {
            "entity": {"type": "company"},
            "criteria": [{"description": "AI companies"}]
        },
        "enrichments": [{"description": "Valuation", "format": "number"}]
    }
    
    parent_mock.request.return_value = mock_response
    
    params = {"query": "AI companies founded after 2020"}
    result = websets_client.preview(params)
    
    parent_mock.request.assert_called_once_with("/websets/v0/websets/preview", data=params, method="POST", params=None)


def test_create_webset_with_scope(websets_client, parent_mock):
    """Test creating webset with scope parameter."""
    mock_response = {
        "id": "ws_123", 
        "object": "webset", 
        "status": "running",
        "searches": [],
        "enrichments": [],
        "monitors": [],
        "createdAt": "2023-01-01T00:00:00Z",
        "updatedAt": "2023-01-01T00:00:00Z"
    }
    parent_mock.request.return_value = mock_response
    
    params = {
        "search": {
            "query": "Tech companies",
            "scope": [{"id": "import_123", "source": "import"}]
        }
    }
    
    result = websets_client.create(params)
    parent_mock.request.assert_called_once_with("/websets/v0/websets", data=params, method="POST", params=None)


# ============================================================================
# Async Tests - Comprehensive Coverage
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

@pytest.mark.asyncio
async def test_async_websets_client_create(async_websets_client, async_parent_mock, sample_webset_data):
    """Test async webset creation."""
    async_parent_mock.async_request.return_value = sample_webset_data
    
    params = CreateWebsetParameters(
        external_id="test-id",
        search=CreateWebsetParametersSearch(query="test query", count=10)
    )
    
    result = await async_websets_client.create(params=params)
    
    # Verify the call was made with correct endpoint and method
    call_args = async_parent_mock.async_request.call_args
    assert call_args[0][0] == "/websets/v0/websets"
    assert call_args[1]["method"] == "POST"
    assert call_args[1]["params"] is None
    # Data should be converted to dict
    assert isinstance(call_args[1]["data"], dict)
    assert call_args[1]["data"]["externalId"] == "test-id"
    assert result.id == "ws_123"
    assert result.external_id == "test-id"

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
async def test_async_websets_client_update(async_websets_client, async_parent_mock, sample_webset_data):
    """Test async webset update."""
    updated_data = {**sample_webset_data, "status": "running"}
    async_parent_mock.async_request.return_value = updated_data
    
    params = UpdateWebsetRequest(metadata={"updated": "true"})
    result = await async_websets_client.update(id="ws_123", params=params)
    
    # Verify the call was made with correct endpoint and method  
    call_args = async_parent_mock.async_request.call_args
    assert call_args[0][0] == "/websets/v0/websets/ws_123"
    assert call_args[1]["method"] == "POST"
    assert call_args[1]["params"] is None
    # Data should be converted to dict
    assert isinstance(call_args[1]["data"], dict)
    assert call_args[1]["data"]["metadata"]["updated"] == "true"
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
                 "websetId": "ws_123", "properties": {
                     "type": "company",
                     "url": "https://example1.com",
                     "description": "Example Company 1",
                     "company": {"name": "Example Corp 1"}
                 }, "evaluations": [], "enrichments": [],
                 "createdAt": "2023-01-01T00:00:00Z", "updatedAt": "2023-01-01T00:00:00Z"}
            ],
            "hasMore": True,
            "nextCursor": "cursor_2"
        }
    
    # Second page response
    second_page = {
            "data": [
                {"id": "item_2", "object": "webset_item", "source": "search", "sourceId": "search_123", 
                 "websetId": "ws_123", "properties": {
                     "type": "company", 
                     "url": "https://example2.com",
                     "description": "Example Company 2",
                     "company": {"name": "Example Corp 2"}
                 }, "evaluations": [], "enrichments": [],
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

@pytest.mark.asyncio
async def test_async_searches_client_create(async_websets_client, async_parent_mock):
    """Test async searches client creation."""
    search_response = {
        "id": "search_123",
        "object": "webset_search",
        "websetId": "ws_123",
        "status": "running",
        "query": "test query",
        "criteria": [],
        "count": 10,
        "progress": {"total": 100, "completed": 0, "found": 5, "completion": 0.0},
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
async def test_async_enrichments_client_create(async_websets_client, async_parent_mock):
    """Test async enrichments client creation."""
    enrichment_response = {
        "id": "enrichment_123",
        "object": "webset_enrichment",
        "websetId": "ws_123",
        "status": "pending",
        "description": "Test enrichment",
        "format": "text",
        "createdAt": "2023-01-01T00:00:00Z",
        "updatedAt": "2023-01-01T00:00:00Z"
    }
    async_parent_mock.async_request.return_value = enrichment_response
    
    params = CreateEnrichmentParameters(description="Test enrichment", format=Format.text)
    result = await async_websets_client.enrichments.create(webset_id="ws_123", params=params)
    
    # Verify the call was made with correct endpoint and method
    call_args = async_parent_mock.async_request.call_args
    assert call_args[0][0] == "/websets/v0/websets/ws_123/enrichments"
    assert call_args[1]["method"] == "POST"
    assert call_args[1]["params"] is None
    # Data should be converted to dict
    assert isinstance(call_args[1]["data"], dict)
    assert call_args[1]["data"]["description"] == "Test enrichment"
    assert call_args[1]["data"]["format"] == "text"
    assert result.id == "enrichment_123"
    assert result.description == "Test enrichment"

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

 