from __future__ import annotations

from pydantic import ConfigDict
from enum import Enum
from typing import Any, Dict, Optional, TypeVar, Generic, Type, get_origin, get_args

from pydantic import BaseModel

# Generic type var for any Enum
EnumT = TypeVar('EnumT', bound=Enum)

class ExaBaseModel(BaseModel):
    """Base model for all Exa models with common configuration."""
    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=False,  # Don't convert enums to strings
        coerce_numbers_to_str=False,  # Don't convert numbers to strings
        str_strip_whitespace=True,  # Strip whitespace from strings
        str_to_lower=False,  # Don't convert strings to lowercase
        str_to_upper=False,  # Don't convert strings to uppercase
        from_attributes=True,  # Allow initialization from attributes
        validate_assignment=True,  # Validate on assignment
        extra='forbid',  # Forbid extra fields
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
        
    def request(self, endpoint: str, data: Optional[Dict[str, Any]] = None, 
                method: str = "POST", params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a request to the Exa API.
        
        Args:
            endpoint (str): The API endpoint to request.
            data (Dict[str, Any], optional): The request data. Defaults to None.
            method (str, optional): The HTTP method. Defaults to "POST".
            params (Dict[str, Any], optional): The query parameters. Defaults to None.
            
        Returns:
            Dict[str, Any]: The API response.
        """
        return self._client.request("/websets/" + endpoint, data=data, method=method, params=params) 
    
