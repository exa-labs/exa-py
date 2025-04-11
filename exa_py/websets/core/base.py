from __future__ import annotations

import json
from pydantic import ConfigDict, BaseModel, AnyUrl
from enum import Enum
from typing import Any, Dict, Optional, TypeVar, Generic, Type, get_origin, get_args, Union

# Generic type var for any Enum
EnumT = TypeVar('EnumT', bound=Enum)

# Generic type for any ExaBaseModel
ModelT = TypeVar('ModelT', bound='ExaBaseModel')

# Custom JSON encoder for handling AnyUrl
class ExaJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, AnyUrl):
            return str(obj)
        return super().default(obj)

class ExaBaseModel(BaseModel):
    """Base model for all Exa models with common configuration."""
    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        coerce_numbers_to_str=False,  # Don't convert numbers to strings
        str_strip_whitespace=True,  # Strip whitespace from strings
        str_to_lower=False,  # Don't convert strings to lowercase
        str_to_upper=False,  # Don't convert strings to uppercase
        from_attributes=True,  # Allow initialization from attributes
        validate_assignment=True,  # Validate on assignment
        extra='forbid',  # Forbid extra fields
        json_encoders={AnyUrl: str}  # Convert AnyUrl to string when serializing to JSON
    )

class WebsetsBaseClient:
    base_url: str

    """Base client for Exa API resources."""

    def __init__(self, client):
        """Initialize the client.
        
        Args:
            client: The parent Exa client.
        """
        self._client = client
        
    def _prepare_data(self, data: Union[Dict[str, Any], ExaBaseModel, str], model_class: Optional[Type[ModelT]] = None) -> Union[Dict[str, Any], str]:
        """Prepare data for API request, converting dict to model if needed.
        
        Args:
            data: Either a dictionary, model instance, or string
            model_class: The model class to use if data is a dictionary
            
        Returns:
            Dictionary prepared for API request or string if string data was provided
        """
        if isinstance(data, str):
            # Return string as is
            return data
        elif isinstance(data, dict) and model_class:
            # Convert dict to model instance
            model_instance = model_class.model_validate(data)
            return model_instance.model_dump(by_alias=True, exclude_none=True)
        elif isinstance(data, ExaBaseModel):
            # Use model's dump method
            return data.model_dump(by_alias=True, exclude_none=True)
        elif isinstance(data, dict):
            # Use dict directly
            return data
        else:
            raise TypeError(f"Expected dict, ExaBaseModel, or str, got {type(data)}")
        
    def request(self, endpoint: str, data: Optional[Union[Dict[str, Any], ExaBaseModel, str]] = None, 
                method: str = "POST", params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a request to the Exa API.
        
        Args:
            endpoint (str): The API endpoint to request.
            data (Union[Dict[str, Any], ExaBaseModel, str], optional): The request data. Can be a dictionary, model instance, or string. Defaults to None.
            method (str, optional): The HTTP method. Defaults to "POST".
            params (Dict[str, Any], optional): The query parameters. Defaults to None.
            
        Returns:
            Dict[str, Any]: The API response.
        """
        if isinstance(data, str):
            # If data is a string, pass it as is
            pass
        elif data is not None and isinstance(data, ExaBaseModel):
            # If data is a model instance, convert it to a dict
            data = data.model_dump(by_alias=True, exclude_none=True)
            
        return self._client.request("/websets/" + endpoint, data=data, method=method, params=params) 
    
