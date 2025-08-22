from __future__ import annotations

import asyncio
from typing import List, Optional, Literal, Dict, Any, Union

from .types import (
    Webset,
    ListWebsetsResponse,
    GetWebsetResponse,
    UpdateWebsetRequest,
    WebsetStatus,
    CreateWebsetParameters,
    PreviewWebsetParameters,
    PreviewWebsetResponse,
)
from .core.async_base import WebsetsAsyncBaseClient
from .async_items.client import AsyncWebsetItemsClient
from .async_searches.client import AsyncWebsetSearchesClient
from .async_enrichments.client import AsyncWebsetEnrichmentsClient
from .async_webhooks.client import AsyncWebsetWebhooksClient
from .async_monitors.client import AsyncMonitorsClient
from .async_imports.client import AsyncImportsClient
from .async_events.client import AsyncEventsClient

class AsyncWebsetsClient(WebsetsAsyncBaseClient):
    """Async client for managing Websets."""
    
    def __init__(self, client):
        super().__init__(client)
        self.items = AsyncWebsetItemsClient(client)
        self.searches = AsyncWebsetSearchesClient(client)
        self.enrichments = AsyncWebsetEnrichmentsClient(client)
        self.webhooks = AsyncWebsetWebhooksClient(client)
        self.monitors = AsyncMonitorsClient(client)
        self.imports = AsyncImportsClient(client)
        self.events = AsyncEventsClient(client)

    async def create(self, params: Union[Dict[str, Any], CreateWebsetParameters]) -> Webset:
        """Create a new Webset.
        
        Args:
            params (CreateWebsetParameters): The parameters for creating a webset.
        
        Returns:
            Webset: The created webset.
        """
        response = await self.request("/v0/websets", data=params)
        return Webset.model_validate(response)

    async def preview(self, params: Union[Dict[str, Any], PreviewWebsetParameters]) -> PreviewWebsetResponse:
        """Preview a Webset before creating it.
        
        Args:
            params (PreviewWebsetParameters): The parameters for previewing a webset.
        
        Returns:
            PreviewWebsetResponse: The preview results.
        """
        response = await self.request("/v0/websets/preview", data=params)
        return PreviewWebsetResponse.model_validate(response)

    async def get(self, id: str, *, expand: Optional[List[Literal["items"]]] = None) -> GetWebsetResponse:
        """Get a Webset by ID.
        
        Args:
            id (str): The id or externalId of the Webset.
            expand (List[Literal["items"]], optional): Expand items in the response.
        
        Returns:
            GetWebsetResponse: The retrieved webset.
        """
        params = {}
        if expand is not None:
            params["expand"] = expand

        response = await self.request(f"/v0/websets/{id}", params=params, method="GET")
        return GetWebsetResponse.model_validate(response)

    async def list(self, *, cursor: Optional[str] = None, limit: Optional[int] = None) -> ListWebsetsResponse:
        """List all Websets.
        
        Args:
            cursor (str, optional): The cursor to paginate through the results.
            limit (int, optional): The number of results to return (max 200).
        
        Returns:
            ListWebsetsResponse: List of websets.
        """
        params = {k: v for k, v in {"cursor": cursor, "limit": limit}.items() if v is not None}
        response = await self.request("/v0/websets", params=params, method="GET")
        return ListWebsetsResponse.model_validate(response)

    async def update(self, id: str, params: Union[Dict[str, Any], UpdateWebsetRequest]) -> Webset:
        """Update a Webset.
        
        Args:
            id (str): The id or externalId of the Webset.
            params (UpdateWebsetRequest): The parameters for updating a webset.
        
        Returns:
            Webset: The updated webset.
        """
        response = await self.request(f"/v0/websets/{id}", data=params, method="POST")
        return Webset.model_validate(response)

    async def delete(self, id: str) -> Webset:
        """Delete a Webset.
        
        Args:
            id (str): The id or externalId of the Webset.
        
        Returns:
            Webset: The deleted webset.
        """
        response = await self.request(f"/v0/websets/{id}", method="DELETE")
        return Webset.model_validate(response)

    async def cancel(self, id: str) -> Webset:
        """Cancel a running Webset.
        
        Args:
            id (str): The id or externalId of the Webset.
        
        Returns:
            Webset: The canceled webset.
        """
        response = await self.request(f"/v0/websets/{id}/cancel", method="POST")
        return Webset.model_validate(response)

    async def wait_until_idle(self, id: str, *, timeout: int = 3600, poll_interval: int = 5) -> Webset:
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
        start_time = asyncio.get_event_loop().time()
        while True:
            webset = await self.get(id)
            if webset.status == WebsetStatus.idle.value:
                return webset
                
            if asyncio.get_event_loop().time() - start_time > timeout:
                raise TimeoutError(f"Webset {id} did not become idle within {timeout} seconds")
                
            await asyncio.sleep(poll_interval)
