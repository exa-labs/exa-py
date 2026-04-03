"""
Tests for Pydantic schema integration with Exa API.

This test file verifies that the new JSONSchemaInput type works correctly
with both Pydantic models and regular dictionaries (backward compatibility).
"""

import pytest
from typing import List, Optional
from unittest.mock import AsyncMock
from pydantic import BaseModel, Field

from exa_py.api import _convert_schema_input, JSONSchemaInput, JSONSchema


class SimpleModel(BaseModel):
    """Simple Pydantic model for testing."""

    name: str = Field(description="The name field")
    age: Optional[int] = Field(default=None, description="The age field")


class NestedModel(BaseModel):
    """Nested Pydantic model for testing."""

    title: str = Field(description="Title of the item")
    tags: List[str] = Field(description="List of tags")
    metadata: Optional[SimpleModel] = Field(default=None, description="Metadata object")


class SnakeCaseModel(BaseModel):
    """Model with snake_case fields to verify schema keys are preserved."""

    company_name: str = Field(description="Company name")
    founded_year: Optional[int] = Field(default=None, description="Founded year")


class TestSchemaConversion:
    """Test the schema conversion function."""

    def test_pydantic_model_conversion(self):
        """Test that Pydantic models are correctly converted to JSON Schema."""
        model = SimpleModel
        result = _convert_schema_input(model)

        # Should return a dictionary (JSON Schema)
        assert isinstance(result, dict)

        # Should have standard JSON Schema fields
        assert "type" in result
        assert result["type"] == "object"
        assert "properties" in result

        # Should have our model fields
        properties = result["properties"]
        assert "name" in properties
        assert "age" in properties

        # Check field descriptions are preserved
        assert properties["name"]["description"] == "The name field"
        assert properties["age"]["description"] == "The age field"

    def test_nested_pydantic_model_conversion(self):
        """Test that nested Pydantic models are correctly converted and inlined."""
        model = NestedModel
        result = _convert_schema_input(model)

        assert isinstance(result, dict)
        assert "properties" in result

        properties = result["properties"]
        assert "title" in properties
        assert "tags" in properties
        assert "metadata" in properties

        # With our inline schema generator, there should be NO $defs
        assert "$defs" not in result
        assert "definitions" not in result

        # The metadata field should have the nested model schema inlined
        metadata_prop = properties["metadata"]

        # metadata is Optional[SimpleModel], so it should be anyOf with null
        assert "anyOf" in metadata_prop
        anyof_schemas = metadata_prop["anyOf"]

        # Should have two options: the SimpleModel schema and null
        assert len(anyof_schemas) == 2

        # Find the SimpleModel schema (not the null type)
        simple_model_schema = None
        for schema in anyof_schemas:
            if schema.get("type") == "object":
                simple_model_schema = schema
                break

        assert simple_model_schema is not None, "Should find inlined SimpleModel schema"

        # Verify the SimpleModel schema is properly inlined
        assert simple_model_schema["title"] == "SimpleModel"
        assert "properties" in simple_model_schema

        # Should have the fields from SimpleModel
        simple_props = simple_model_schema["properties"]
        assert "name" in simple_props
        assert "age" in simple_props

        # Verify field descriptions are preserved
        assert simple_props["name"]["description"] == "The name field"
        assert simple_props["age"]["description"] == "The age field"

    def test_dict_passthrough(self):
        """Test that dictionaries are passed through unchanged."""
        schema_dict = {
            "type": "object",
            "properties": {
                "test_field": {"type": "string", "description": "A test field"}
            },
            "required": ["test_field"],
        }

        result = _convert_schema_input(schema_dict)

        # Should be the exact same dictionary
        assert result == schema_dict
        assert result is schema_dict  # Should be the same object

    def test_legacy_jsonschema_support(self):
        """Test that legacy JSONSchema TypedDict instances work."""
        legacy_schema: JSONSchema = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "number"}},
            "required": ["name"],
        }

        result = _convert_schema_input(legacy_schema)

        # Should work as a regular dict
        assert isinstance(result, dict)
        assert result["type"] == "object"
        assert "name" in result["properties"]

    def test_invalid_type_raises_error(self):
        """Test that invalid types raise appropriate errors."""
        with pytest.raises(ValueError, match="Unsupported schema type"):
            _convert_schema_input("invalid_string")

        with pytest.raises(ValueError, match="Unsupported schema type"):
            _convert_schema_input(123)

        with pytest.raises(ValueError, match="Unsupported schema type"):
            _convert_schema_input([1, 2, 3])


class TestTypeAnnotations:
    """Test that type annotations work correctly."""

    def test_jsonschema_input_accepts_pydantic(self):
        """Test that JSONSchemaInput type accepts Pydantic models."""

        # This is mainly for type checker validation
        def accepts_schema_input(schema: JSONSchemaInput) -> dict:
            return _convert_schema_input(schema)

        # Should accept Pydantic model
        result1 = accepts_schema_input(SimpleModel)
        assert isinstance(result1, dict)

        # Should accept dict
        dict_schema = {"type": "object", "properties": {}}
        result2 = accepts_schema_input(dict_schema)
        assert isinstance(result2, dict)

    def test_backward_compatibility_with_typeddict(self):
        """Test that old JSONSchema TypedDict usage still works."""
        # This simulates the old usage pattern
        old_style_schema: JSONSchema = {
            "type": "object",
            "properties": {
                "company_name": {"type": "string"},
                "industry": {"type": "string"},
            },
        }

        # Should still work with new conversion function
        result = _convert_schema_input(old_style_schema)
        assert result == old_style_schema


class TestIntegrationMocking:
    """Test integration with mocked Exa API calls."""

    def test_summary_with_pydantic_model(self, mocker):
        """Test that summary options work with Pydantic models."""
        from exa_py import Exa

        # Mock the request method
        mock_request = mocker.patch.object(Exa, "request")
        mock_request.return_value = {
            "results": [],
            "autopromptString": "test",
            "resolvedSearchType": "neural",
        }

        exa = Exa("test_api_key")

        # This should not raise an error and should convert the schema
        exa.search_and_contents("test query", summary={"schema": SimpleModel})

        # Verify the request was called
        mock_request.assert_called_once()

        # Get the actual call arguments
        call_args = mock_request.call_args
        assert call_args[0][0] == "/search"  # endpoint

        # The payload should have the converted schema
        payload = call_args[0][1]
        assert "contents" in payload
        assert "summary" in payload["contents"]
        assert "schema" in payload["contents"]["summary"]

        # The schema should be a dict (converted from Pydantic)
        converted_schema = payload["contents"]["summary"]["schema"]
        assert isinstance(converted_schema, dict)
        assert converted_schema["type"] == "object"

    def test_answer_with_pydantic_model(self, mocker):
        """Test that answer endpoint works with Pydantic models."""
        from exa_py import Exa

        # Mock the request method
        mock_request = mocker.patch.object(Exa, "request")
        mock_request.return_value = {"answer": "test answer", "citations": []}

        exa = Exa("test_api_key")

        # This should not raise an error and should convert the schema
        exa.answer("test query", output_schema=SimpleModel)

        # Verify the request was called
        mock_request.assert_called_once()

        # Get the actual call arguments
        call_args = mock_request.call_args
        assert call_args[0][0] == "/answer"  # endpoint

        # The payload should have the converted schema
        payload = call_args[0][1]
        assert "outputSchema" in payload

        # The schema should be a dict (converted from Pydantic)
        converted_schema = payload["outputSchema"]
        assert isinstance(converted_schema, dict)
        assert converted_schema["type"] == "object"

    def test_answer_returns_parsed_output_for_pydantic_model(self, mocker):
        """Test that answer responses expose parsed_output for Pydantic schemas."""
        from exa_py import Exa

        mock_request = mocker.patch.object(Exa, "request")
        mock_request.return_value = {
            "answer": {"name": "Ada", "age": 37},
            "citations": [],
        }

        exa = Exa("test_api_key")
        response = exa.answer("test query", output_schema=SimpleModel)

        assert response.answer == {"name": "Ada", "age": 37}
        assert isinstance(response.parsed_output, SimpleModel)
        assert response.parsed_output.name == "Ada"
        assert response.parsed_output.age == 37

    def test_get_contents_returns_parsed_summary_for_pydantic_model(self, mocker):
        """Test that get_contents responses expose parsed_summary for Pydantic schemas."""
        from exa_py import Exa

        mock_request = mocker.patch.object(Exa, "request")
        mock_request.return_value = {
            "results": [
                {
                    "url": "https://example.com",
                    "id": "1",
                    "summary": '{"company_name":"Exa","founded_year":2021}',
                }
            ],
            "statuses": [],
        }

        exa = Exa("test_api_key")
        response = exa.get_contents(
            "https://example.com",
            summary={"schema": SnakeCaseModel},
        )

        parsed_summary = response.results[0].parsed_summary
        assert isinstance(parsed_summary, SnakeCaseModel)
        assert parsed_summary.company_name == "Exa"
        assert parsed_summary.founded_year == 2021

        payload = mock_request.call_args[0][1]
        converted_schema = payload["summary"]["schema"]
        assert "company_name" in converted_schema["properties"]
        assert "companyName" not in converted_schema["properties"]

    def test_search_returns_parsed_content_for_pydantic_output_schema(self, mocker):
        """Test that deep search responses expose parsed_content for Pydantic schemas."""
        from exa_py import Exa

        mock_request = mocker.patch.object(Exa, "request")
        mock_request.return_value = {
            "results": [],
            "output": {
                "content": {"name": "Ada", "age": 37},
                "grounding": [],
            },
        }

        exa = Exa("test_api_key")
        response = exa.search(
            "test query",
            type="deep",
            contents=False,
            output_schema=SimpleModel,
        )

        assert response.output is not None
        assert isinstance(response.output.parsed_content, SimpleModel)
        assert response.output.parsed_content.name == "Ada"
        assert response.output.parsed_content.age == 37

        payload = mock_request.call_args[0][1]
        converted_schema = payload["outputSchema"]
        assert converted_schema["properties"]["name"]["type"] == "string"

    def test_search_contents_summary_preserves_schema_field_names(self, mocker):
        """Test that modern search summary schemas keep snake_case property names."""
        from exa_py import Exa

        mock_request = mocker.patch.object(Exa, "request")
        mock_request.return_value = {
            "results": [
                {
                    "url": "https://example.com",
                    "id": "1",
                    "summary": '{"company_name":"Exa","founded_year":2021}',
                }
            ],
        }

        exa = Exa("test_api_key")
        response = exa.search(
            "test query",
            contents={"summary": {"schema": SnakeCaseModel}},
            num_results=1,
        )

        parsed_summary = response.results[0].parsed_summary
        assert isinstance(parsed_summary, SnakeCaseModel)
        assert parsed_summary.company_name == "Exa"

        payload = mock_request.call_args[0][1]
        converted_schema = payload["contents"]["summary"]["schema"]
        assert "company_name" in converted_schema["properties"]
        assert "companyName" not in converted_schema["properties"]

    @pytest.mark.asyncio
    async def test_async_answer_returns_parsed_output_for_pydantic_model(self, mocker):
        """Test that async answer responses expose parsed_output for Pydantic schemas."""
        from exa_py import AsyncExa

        exa = AsyncExa("test_api_key")
        mock_async_request = mocker.patch.object(exa, "async_request", new=AsyncMock())
        mock_async_request.return_value = {
            "answer": {"name": "Ada", "age": 37},
            "citations": [],
        }

        response = await exa.answer("test query", output_schema=SimpleModel)

        assert response.answer == {"name": "Ada", "age": 37}
        assert isinstance(response.parsed_output, SimpleModel)
        assert response.parsed_output.name == "Ada"
        assert response.parsed_output.age == 37

    @pytest.mark.asyncio
    async def test_async_get_contents_returns_parsed_summary_for_pydantic_model(
        self, mocker
    ):
        """Test that async get_contents responses expose parsed_summary for Pydantic schemas."""
        from exa_py import AsyncExa

        exa = AsyncExa("test_api_key")
        mock_async_request = mocker.patch.object(exa, "async_request", new=AsyncMock())
        mock_async_request.return_value = {
            "results": [
                {
                    "url": "https://example.com",
                    "id": "1",
                    "summary": '{"company_name":"Exa","founded_year":2021}',
                }
            ],
            "statuses": [],
        }

        response = await exa.get_contents(
            "https://example.com",
            summary={"schema": SnakeCaseModel},
        )

        parsed_summary = response.results[0].parsed_summary
        assert isinstance(parsed_summary, SnakeCaseModel)
        assert parsed_summary.company_name == "Exa"
        assert parsed_summary.founded_year == 2021

    @pytest.mark.asyncio
    async def test_async_search_returns_parsed_content_for_pydantic_output_schema(
        self, mocker
    ):
        """Test that async deep search responses expose parsed_content for Pydantic schemas."""
        from exa_py import AsyncExa

        exa = AsyncExa("test_api_key")
        mock_async_request = mocker.patch.object(exa, "async_request", new=AsyncMock())
        mock_async_request.return_value = {
            "results": [],
            "output": {
                "content": {"name": "Ada", "age": 37},
                "grounding": [],
            },
        }

        response = await exa.search(
            "test query",
            type="deep",
            contents=False,
            output_schema=SimpleModel,
        )

        assert response.output is not None
        assert isinstance(response.output.parsed_content, SimpleModel)
        assert response.output.parsed_content.name == "Ada"
        assert response.output.parsed_content.age == 37
