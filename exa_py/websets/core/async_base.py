from __future__ import annotations

import json
import asyncio
from typing import Any, Dict, Optional, Type, TypeVar, Union

from .base import ExaBaseModel

# Generic type for any ExaBaseModel
ModelT = TypeVar('ModelT', bound=ExaBaseModel)



class WebsetsAsyncBaseClient:
    base_url: str

    """Base async client for Exa API resources."""

    def __init__(self, client):
        """Initialize the async client.
        
        Args:
            client: The parent AsyncExa client.
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
            return model_instance.model_dump(mode='json', by_alias=True, exclude_none=True)
        elif isinstance(data, ExaBaseModel):
            # Use model's dump method
            return data.model_dump(mode='json', by_alias=True, exclude_none=True)
        elif isinstance(data, dict):
            # Use dict directly
            return data
        else:
            raise TypeError(f"Expected dict, ExaBaseModel, or str, got {type(data)}")
        
    async def request(self, endpoint: str, data: Optional[Union[Dict[str, Any], ExaBaseModel, str]] = None, 
                method: str = "POST", params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make an async request to the Exa API.
        
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
            data = data.model_dump(mode='json', by_alias=True, exclude_none=True)
            
        # Ensure proper URL construction by removing leading slash from endpoint if present
        if endpoint.startswith("/"):
            endpoint = endpoint[1:]
            
        return await self._client.async_request("/websets/" + endpoint, data=data, method=method, params=params) 
