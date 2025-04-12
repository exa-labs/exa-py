from __future__ import annotations

from typing import Dict, Any, Union

from ..types import (
    CreateWebsetSearchParameters,
    WebsetSearch,
)
from ..core.base import WebsetsBaseClient

class WebsetSearchesClient(WebsetsBaseClient):
    """Client for managing Webset Searches."""
    
    def __init__(self, client):
        super().__init__(client)

    def create(self, webset_id: str, params: Union[Dict[str, Any], CreateWebsetSearchParameters]) -> WebsetSearch:
        """Create a new Search for the Webset.
        
        Args:
            webset_id (str): The id of the Webset.
            params (CreateWebsetSearchParameters): The parameters for creating a search.
        
        Returns:
            WebsetSearch: The created search.
        """
        response = self.request(f"/v0/websets/{webset_id}/searches", data=params)
        return WebsetSearch.model_validate(response)

    def get(self, webset_id: str, id: str) -> WebsetSearch:
        """Get a Search by ID.
        
        Args:
            webset_id (str): The id of the Webset.
            id (str): The id of the Search.
        
        Returns:
            WebsetSearch: The retrieved search.
        """
        response = self.request(f"/v0/websets/{webset_id}/searches/{id}", method="GET")
        return WebsetSearch.model_validate(response)

    def cancel(self, webset_id: str, id: str) -> WebsetSearch:
        """Cancel a running Search.
        
        Args:
            webset_id (str): The id of the Webset.
            id (str): The id of the Search.
        
        Returns:
            WebsetSearch: The canceled search.
        """
        response = self.request(f"/v0/websets/{webset_id}/searches/{id}/cancel", method="POST")
        return WebsetSearch.model_validate(response) 