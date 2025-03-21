
from __future__ import annotations

from pydantic import ConfigDict

from typing import Any, Dict, Optional

from pydantic import BaseModel

class ExaBaseModel(BaseModel):
    """Base model for all Exa models with common configuration."""
    model_config = ConfigDict(populate_by_name=True)

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
    
