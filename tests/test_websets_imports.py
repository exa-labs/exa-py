from datetime import datetime
import json
import time
from typing import Dict, Any
from unittest.mock import MagicMock, patch

import pytest

from exa_py.websets.imports.client import ImportsClient
from exa_py.websets.types import (
    CreateImportParameters,
    UpdateImport,
    ImportFormat,
    WebsetCompanyEntity,
    WebsetPersonEntity,
    CsvImportConfig,
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
    """Mock parent client."""
    mock = MagicMock()
    return mock

@pytest.fixture
def imports_client(parent_mock):
    """Create ImportsClient with mocked parent."""
    return ImportsClient(parent_mock)

@pytest.fixture
def sample_create_import_response():
    """Sample response for create import."""
    return {
        "id": "import_123",
        "object": "import",
        "title": "Sample Company Data",
        "format": "csv",
        "entity": {"type": "company"},
        "size": 1024.0,
        "count": 100.0,
        "status": "pending",
        "csv": {"identifier": 1},
        "metadata": {"source": "test"},
        "createdAt": "2023-01-01T00:00:00Z",
        "updatedAt": "2023-01-01T00:00:00Z",
        "uploadUrl": "https://example.com/upload",
        "uploadValidUntil": "2023-01-01T01:00:00Z",
        "failedAt": None,
        "failedReason": None,
        "failedMessage": None
    }

@pytest.fixture
def sample_import_response():
    """Sample response for import."""
    return {
        "id": "import_123",
        "object": "import",
        "title": "Sample Company Data",
        "format": "csv",
        "entity": {"type": "company"},
        "size": 1024.0,
        "count": 100.0,
        "status": "completed",
        "csv": {"identifier": 1},
        "metadata": {"source": "test"},
        "createdAt": "2023-01-01T00:00:00Z",
        "updatedAt": "2023-01-01T00:05:00Z",
        "completedAt": "2023-01-01T00:05:00Z",
        "failedAt": None,
        "failedReason": None,
        "failedMessage": None
    }

@pytest.fixture
def sample_failed_import_response():
    """Sample failed import response data."""
    return {
        "id": "import_failed",
        "object": "import",
        "status": "failed",
        "format": "csv",
        "entity": {"type": "company"},
        "title": "Failed Import",
        "count": 0.0,
        "metadata": {},
        "failedReason": "invalid_format",
        "failedAt": "2023-01-01T00:30:00Z",
        "failedMessage": "Invalid CSV format detected",
        "createdAt": "2023-01-01T00:00:00Z",
        "updatedAt": "2023-01-01T00:30:00Z"
    }

# ============================================================================
# ImportsClient Tests
# ============================================================================

def test_create_import_basic(imports_client, parent_mock, sample_create_import_response):
    """Test basic import creation."""
    parent_mock.request.return_value = sample_create_import_response

    params = CreateImportParameters(
        title="Sample Company Data",
        format=ImportFormat.csv,
        entity=WebsetCompanyEntity(type="company"),
        size=1024.0,
        count=100
    )

    result = imports_client.create(params)

    # Verify the result
    assert result.id == "import_123"
    assert result.title == "Sample Company Data"
    assert result.format == "csv"
    assert result.status == "pending"
    
    # Verify request was called
    parent_mock.request.assert_called_once()

def test_create_import_with_dict_params(imports_client, parent_mock, sample_create_import_response):
    """Test creating import with dictionary parameters."""
    parent_mock.request.return_value = sample_create_import_response

    params = {
        "title": "Dict Import",
        "format": "csv",
        "entity": {"type": "company"},
        "size": 512.0,
        "count": 50
    }

    result = imports_client.create(params)

    assert result.id == "import_123"
    parent_mock.request.assert_called_once()

def test_get_import(imports_client, parent_mock, sample_import_response):
    """Test getting a specific import."""
    parent_mock.request.return_value = sample_import_response

    result = imports_client.get("import_123")

    assert result.id == "import_123"
    assert result.status == "completed"
    parent_mock.request.assert_called_once()

def test_list_imports(imports_client, parent_mock, sample_import_response):
    """Test listing imports."""
    response_data = {
        "data": [sample_import_response],
        "hasMore": True,
        "nextCursor": "cursor_123"
    }
    parent_mock.request.return_value = response_data

    result = imports_client.list(cursor="prev_cursor", limit=25)

    assert len(result.data) == 1
    assert result.has_more is True
    assert result.next_cursor == "cursor_123"
    parent_mock.request.assert_called_once()

def test_update_import(imports_client, parent_mock, sample_import_response):
    """Test updating an import."""
    updated_response = sample_import_response.copy()
    updated_response["title"] = "Updated Title"
    parent_mock.request.return_value = updated_response

    params = UpdateImport(title="Updated Title")
    result = imports_client.update("import_123", params)

    assert result.title == "Updated Title"
    parent_mock.request.assert_called_once()

def test_update_import_with_dict(imports_client, parent_mock, sample_import_response):
    """Test updating import with dictionary parameters."""
    updated_response = sample_import_response.copy()
    updated_response["title"] = "Dict Updated"
    parent_mock.request.return_value = updated_response

    params = {"title": "Dict Updated"}
    result = imports_client.update("import_123", params)

    assert result.title == "Dict Updated"
    parent_mock.request.assert_called_once()

def test_delete_import(imports_client, parent_mock, sample_import_response):
    """Test deleting an import."""
    parent_mock.request.return_value = sample_import_response

    result = imports_client.delete("import_123")

    assert result.id == "import_123"
    parent_mock.request.assert_called_once()

# ============================================================================
# wait_until_completed Tests
# ============================================================================

@patch('time.sleep')
@patch('time.time')
def test_wait_until_completed_success(mock_time, mock_sleep, imports_client, parent_mock, sample_import_response):
    """Test waiting until import completes successfully."""
    # Mock time to control timeout
    mock_time.side_effect = [0, 10, 15]  # Start time, first check, second check
    
    # First call returns pending, second returns completed
    pending_response = sample_import_response.copy()
    pending_response["status"] = "pending"
    completed_response = sample_import_response.copy()
    completed_response["status"] = "completed"
    
    parent_mock.request.side_effect = [pending_response, completed_response]

    result = imports_client.wait_until_completed("import_123")

    assert result.status == "completed"
    assert parent_mock.request.call_count == 2
    mock_sleep.assert_called_once_with(5)

@patch('time.sleep')
@patch('time.time')
def test_wait_until_completed_timeout(mock_time, mock_sleep, imports_client, parent_mock, sample_import_response):
    """Test timeout when waiting for import completion."""
    # Mock time to simulate timeout
    mock_time.side_effect = [0, 10, 20, 30, 40]  # Exceed timeout
    
    pending_response = sample_import_response.copy()
    pending_response["status"] = "pending"
    parent_mock.request.return_value = pending_response

    with pytest.raises(TimeoutError, match="did not complete within 30 seconds"):
        imports_client.wait_until_completed("import_123", timeout=30)

    assert parent_mock.request.call_count >= 1

# ============================================================================
# Error Handling Tests
# ============================================================================

def test_create_import_request_error(imports_client, parent_mock):
    """Test that client properly handles request errors on create."""
    parent_mock.request.side_effect = Exception("Network error")
    
    params = CreateImportParameters(
        title="Test",
        format=ImportFormat.csv,
        entity=WebsetCompanyEntity(type="company"),
        size=100.0,
        count=10
    )
    
    with pytest.raises(Exception, match="Network error"):
        imports_client.create(params)

def test_get_import_not_found(imports_client, parent_mock):
    """Test handling of import not found error."""
    parent_mock.request.side_effect = Exception("Import not found")
    
    with pytest.raises(Exception, match="Import not found"):
        imports_client.get("nonexistent_import")

def test_wait_until_completed_get_error(imports_client, parent_mock):
    """Test wait_until_completed when get request fails."""
    parent_mock.request.side_effect = Exception("API error")
    
    with pytest.raises(Exception, match="API error"):
        imports_client.wait_until_completed("import_123")

# ============================================================================
# Field Serialization Tests
# ============================================================================

def test_case_conversion_in_import_params(imports_client, parent_mock, sample_create_import_response):
    """Test that camelCase fields are properly handled."""
    parent_mock.request.return_value = sample_create_import_response
    
    params = CreateImportParameters(
        title="Test Import",
        format=ImportFormat.csv,
        entity=WebsetCompanyEntity(type="company"),
        size=1024.0,
        count=50,
        csv=CsvImportConfig(identifier=1)
    )
    
    result = imports_client.create(params)
    
    # Verify the response properly maps camelCase back to snake_case
    assert result.created_at is not None  # createdAt -> created_at
    assert result.updated_at is not None  # updatedAt -> updated_at
    assert result.upload_url is not None  # uploadUrl -> upload_url
    assert result.upload_valid_until is not None  # uploadValidUntil -> upload_valid_until

def test_enum_serialization(imports_client, parent_mock, sample_create_import_response):
    """Test that enums are properly serialized."""
    parent_mock.request.return_value = sample_create_import_response

    params = CreateImportParameters(
        title="Enum Test",
        format=ImportFormat.webset,  # Using enum
        entity=WebsetPersonEntity(type="person"),
        size=1024.0,
        count=100
    )

    result = imports_client.create(params)
    
    assert result.id == "import_123"
    parent_mock.request.assert_called_once()

def test_optional_fields_handling(imports_client, parent_mock, sample_create_import_response):
    """Test handling of optional fields."""
    parent_mock.request.return_value = sample_create_import_response

    # Create with minimal required fields (size and count are required)
    params = CreateImportParameters(
        title="Minimal Import",
        format=ImportFormat.csv,
        entity=WebsetCompanyEntity(type="company"),
        size=1024.0,
        count=100
    )

    result = imports_client.create(params)
    
    assert result.id == "import_123"
    parent_mock.request.assert_called_once()

def test_metadata_preservation(imports_client, parent_mock, sample_import_response):
    """Test that metadata keys preserve their original case format."""
    test_metadata = {
        "snake_case_key": "value1",
        "camelCaseKey": "value2",
        "UPPER_CASE": "value3"
    }
    
    updated_response = sample_import_response.copy()
    updated_response["metadata"] = test_metadata
    parent_mock.request.return_value = updated_response
    
    params = UpdateImport(metadata=test_metadata)
    result = imports_client.update("import_123", params)
    
    assert result.metadata == test_metadata
    
    # Verify the request preserves metadata case
    call_data = parent_mock.request.call_args[1]['data']
    assert call_data["metadata"] == test_metadata

# ============================================================================
# Integration Tests
# ============================================================================

def test_full_import_lifecycle(imports_client, parent_mock):
    """Test a complete import lifecycle: create -> wait -> update -> delete."""
    # Create response
    create_response = {
        "id": "import_lifecycle",
        "object": "import",
        "status": "pending",
        "format": "csv",
        "entity": {"type": "company"},
        "title": "Lifecycle Test",
        "count": 10.0,
        "metadata": {},
        "createdAt": "2023-01-01T00:00:00Z",
        "updatedAt": "2023-01-01T00:00:00Z",
        "uploadUrl": "https://upload.example.com/import_lifecycle",
        "uploadValidUntil": "2023-01-01T01:00:00Z"
    }
    
    # Processing response
    processing_response = create_response.copy()
    processing_response["status"] = "processing"
    del processing_response["uploadUrl"]
    del processing_response["uploadValidUntil"]
    
    # Completed response
    completed_response = processing_response.copy()
    completed_response["status"] = "completed"
    
    # Updated response
    updated_response = completed_response.copy()
    updated_response["title"] = "Updated Lifecycle Test"
    
    # Set up mock calls in sequence
    parent_mock.request.side_effect = [
        create_response,      # create
        processing_response,  # wait_until_completed first check
        completed_response,   # wait_until_completed second check (completed)
        updated_response,     # update
        updated_response      # delete
    ]
    
    with patch('time.sleep'):
        # Create
        create_result = imports_client.create({
            "title": "Lifecycle Test",
            "format": "csv",
            "entity": {"type": "company"},
            "size": 100.0,
            "count": 10
        })
        assert create_result.status == "pending"
        
        # Wait for completion
        completed_result = imports_client.wait_until_completed("import_lifecycle")
        assert completed_result.status == "completed"
        
        # Update
        updated_result = imports_client.update("import_lifecycle", {
            "title": "Updated Lifecycle Test"
        })
        assert updated_result.title == "Updated Lifecycle Test"
        
        # Delete
        deleted_result = imports_client.delete("import_lifecycle")
        assert deleted_result.id == "import_lifecycle"
    
    # Verify all calls were made
    assert parent_mock.request.call_count == 5 