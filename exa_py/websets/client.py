from __future__ import annotations

import time
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
    RequestOptions,
)
from .core.base import WebsetsBaseClient
from .core.async_base import WebsetsAsyncBaseClient
from .items import WebsetItemsClient, AsyncWebsetItemsClient
from .searches import WebsetSearchesClient, AsyncWebsetSearchesClient
from .enrichments import WebsetEnrichmentsClient, AsyncWebsetEnrichmentsClient
from .webhooks import WebsetWebhooksClient, AsyncWebsetWebhooksClient
from .monitors import MonitorsClient, AsyncMonitorsClient
from .imports import ImportsClient, AsyncImportsClient
from .events import EventsClient, AsyncEventsClient

class WebsetsClient(WebsetsBaseClient):
    """Client for managing Websets."""
    
    def __init__(self, client):
        super().__init__(client)
        self.items = WebsetItemsClient(client)
        self.searches = WebsetSearchesClient(client)
        self.enrichments = WebsetEnrichmentsClient(client)
        self.webhooks = WebsetWebhooksClient(client)
        self.monitors = MonitorsClient(client)
        self.imports = ImportsClient(client)
        self.events = EventsClient(client)

    def create(self, params: Union[Dict[str, Any], CreateWebsetParameters], 
               options: Optional[Union[Dict[str, Any], RequestOptions]] = None) -> Webset:
        """Create a new Webset.
        
        Args:
            params (CreateWebsetParameters): The parameters for creating a webset.
            options (RequestOptions, optional): Request options including priority and/or custom headers.
                Can specify priority as 'low', 'medium', or 'high'.
        
        Returns:
            Webset: The created webset.
        """
        response = self.request("/v0/websets", data=params, options=options)
        return Webset.model_validate(response)

    def preview(self, params: Union[Dict[str, Any], PreviewWebsetParameters]) -> PreviewWebsetResponse:
        """Preview a webset query.
        
        Preview how a search query will be decomposed before creating a webset. 
        This endpoint performs the same query analysis that happens during webset creation, 
        allowing you to see the detected entity type, generated search criteria, and 
        available enrichment columns in advance.
        
        Args:
            params (PreviewWebsetParameters): The parameters for previewing a webset.
        
        Returns:
            PreviewWebsetResponse: The preview response showing how the query will be decomposed.
        """
        response = self.request("/v0/websets/preview", data=params)
        return PreviewWebsetResponse.model_validate(response)

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

    async def create(self, params: Union[Dict[str, Any], CreateWebsetParameters],
                     options: Optional[Union[Dict[str, Any], RequestOptions]] = None) -> Webset:
        """Create a new Webset.
        
        Args:
            params (CreateWebsetParameters): The parameters for creating a webset.
            options (RequestOptions, optional): Request options including priority and/or custom headers.
                Can specify priority as 'low', 'medium', or 'high'.
        
        Returns:
            Webset: The created webset.
        """
        response = await self.request("/v0/websets", data=params, options=options)
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
