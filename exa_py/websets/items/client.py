from __future__ import annotations

from typing import  Optional

from ..types import (
    WebsetItem,
    ListWebsetItemResponse,
)
from ..core.base import WebsetsBaseClient

class WebsetItemsClient(WebsetsBaseClient):
    """Client for managing Webset Items."""
    
    def __init__(self, client):
        super().__init__(client)

    def list(self, webset_id: str, *, cursor: Optional[str] = None, 
             limit: Optional[int] = None) -> ListWebsetItemResponse:
        """List all Items for a Webset.
        
        Args:
            webset_id (str): The id or externalId of the Webset.
            cursor (str, optional): The cursor to paginate through the results.
            limit (int, optional): The number of results to return (max 200).
        
        Returns:
            ListWebsetItemResponse: List of webset items.
        """
        params = {k: v for k, v in {"cursor": cursor, "limit": limit}.items() if v is not None}
        response = self.request(f"/v0/websets/{webset_id}/items", params=params, method="GET")
        return ListWebsetItemResponse.model_validate(response)

    def retrieve(self, webset_id: str, id: str) -> WebsetItem:
        """Get an Item by ID.
        
        Args:
            webset_id (str): The id or externalId of the Webset.
            id (str): The id of the Webset item.
        
        Returns:
            WebsetItem: The retrieved item.
        """
        response = self.request(f"/v0/websets/{webset_id}/items/{id}", method="GET")
        return WebsetItem.model_validate(response)

    def delete(self, webset_id: str, id: str) -> WebsetItem:
        """Delete an Item.
        
        Args:
            webset_id (str): The id or externalId of the Webset.
            id (str): The id of the Webset item.
        
        Returns:
            WebsetItem: The deleted item.
        """
        response = self.request(f"/v0/websets/{webset_id}/items/{id}", method="DELETE")
        return WebsetItem.model_validate(response) 