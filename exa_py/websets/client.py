from __future__ import annotations

import time
from datetime import datetime
from typing import List, Optional, Literal, Dict, Any, Union

from .types import (
    Webset,
    ListWebsetsResponse,
    GetWebsetResponse,
    UpdateWebsetRequest,
    WebsetStatus,
    CreateWebsetParameters,
)
from .core.base import WebsetsBaseClient
from .items import WebsetItemsClient
from .searches import WebsetSearchesClient
from .enrichments import WebsetEnrichmentsClient
from .webhooks import WebsetWebhooksClient

class WebsetsClient(WebsetsBaseClient):
    """Client for managing Websets."""
    
    def __init__(self, client):
        super().__init__(client)
        self.items = WebsetItemsClient(client)
        self.searches = WebsetSearchesClient(client)
        self.enrichments = WebsetEnrichmentsClient(client)
        self.webhooks = WebsetWebhooksClient(client)

    def create(self, params: Union[Dict[str, Any], CreateWebsetParameters]) -> Webset:
        """Create a new Webset.
        
        Args:
            params (CreateWebsetParameters): The parameters for creating a webset.
        
        Returns:
            Webset: The created webset.
        """
        response = self.request("/v0/websets", data=params)
        return Webset.model_validate(response)

    def get(self, id: str, *, expand: Optional[List[Literal["items"]]] = None) -> GetWebsetResponse:
        """Get a Webset by ID.
        
        Args:
            id (str): The id or externalId of the Webset.
            expand (List[Literal["items"]], optional): Expand the response with specified resources.
                Allowed values: ["items"]
        
        Returns:
            GetWebsetResponse: The retrieved webset.
        """
        params = {"expand": expand} if expand else {}
        response = self.request(f"/v0/websets/{id}", params=params, method="GET")
        return GetWebsetResponse.model_validate(response)

    def list(self, *, cursor: Optional[str] = None, limit: Optional[int] = None) -> ListWebsetsResponse:
        """List all Websets.
        
        Args:
            cursor (str, optional): The cursor to paginate through the results.
            limit (int, optional): The number of results to return (max 200).
        
        Returns:
            ListWebsetsResponse: List of websets.
        """
        params = {k: v for k, v in {"cursor": cursor, "limit": limit}.items() if v is not None}
        response = self.request("/v0/websets", params=params, method="GET")
        return ListWebsetsResponse.model_validate(response)

    def update(self, id: str, params: Union[Dict[str, Any], UpdateWebsetRequest]) -> Webset:
        """Update a Webset.
        
        Args:
            id (str): The id or externalId of the Webset.
            params (UpdateWebsetRequest): The parameters for updating a webset.
        
        Returns:
            Webset: The updated webset.
        """
        response = self.request(f"/v0/websets/{id}", data=params, method="POST")
        return Webset.model_validate(response)

    def delete(self, id: str) -> Webset:
        """Delete a Webset.
        
        Args:
            id (str): The id or externalId of the Webset.
        
        Returns:
            Webset: The deleted webset.
        """
        response = self.request(f"/v0/websets/{id}", method="DELETE")
        return Webset.model_validate(response)

    def cancel(self, id: str) -> Webset:
        """Cancel a running Webset.
        
        Args:
            id (str): The id or externalId of the Webset.
        
        Returns:
            Webset: The canceled webset.
        """
        response = self.request(f"/v0/websets/{id}/cancel", method="POST")
        return Webset.model_validate(response)

    def wait_until_idle(self, id: str, *, timeout: int = 3600, poll_interval: int = 5) -> Webset:
        """Wait until a Webset is idle.
        
        Args:
            id (str): The id or externalId of the Webset.
            timeout (int, optional): Maximum time to wait in seconds. Defaults to 3600.
            poll_interval (int, optional): Time to wait between polls in seconds. Defaults to 5.
            
        Returns:
            Webset: The webset once it's idle.
            
        Raises:
            TimeoutError: If the webset does not become idle within the timeout period.
        """
        start_time = time.time()
        while True:
            webset = self.get(id)
            if webset.status == WebsetStatus.idle.value:
                return webset
                
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Webset {id} did not become idle within {timeout} seconds")
                
            time.sleep(poll_interval)
