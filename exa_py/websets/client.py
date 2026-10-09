from __future__ import annotations

import time
import asyncio
from typing import List, Optional, Literal, Dict, Any, Union, Iterator, AsyncIterator, Callable
from typing_extensions import Unpack

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
from ..request_options import ExtraRequestOptions, options_for_next_page

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
               options: Optional[Union[Dict[str, Any], RequestOptions]] = None, **extra: Unpack[ExtraRequestOptions]) -> Webset:
        """Create a new Webset.
        
        Args:
            params (CreateWebsetParameters): The parameters for creating a webset.
            options (RequestOptions, optional): Request options including priority and/or custom headers.
                Can specify priority as 'low', 'medium', or 'high'.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).
        
        Returns:
            Webset: The created webset.
        """
        response = self.request("/v0/websets", data=params, options=options, **extra)
        return Webset.model_validate(response)

    def preview(self, params: Union[Dict[str, Any], PreviewWebsetParameters], **extra: Unpack[ExtraRequestOptions]) -> PreviewWebsetResponse:
        """Preview a webset query.
        
        Preview how a search query will be decomposed before creating a webset. 
        This endpoint performs the same query analysis that happens during webset creation, 
        allowing you to see the detected entity type, generated search criteria, and 
        available enrichment columns in advance.
        
        Args:
            params (PreviewWebsetParameters): The parameters for previewing a webset.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).
        
        Returns:
            PreviewWebsetResponse: The preview response showing how the query will be decomposed.
        """
        response = self.request("/v0/websets/preview", data=params, **extra)
        return PreviewWebsetResponse.model_validate(response)

    def get(self, id: str, *, expand: Optional[List[Literal["items"]]] = None, **extra: Unpack[ExtraRequestOptions]) -> GetWebsetResponse:
        """Get a Webset by ID.
        
        Args:
            id (str): The id or externalId of the Webset.
            expand (List[Literal["items"]], optional): Expand the response with specified resources.
                Allowed values: ["items"]
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).
        
        Returns:
            GetWebsetResponse: The retrieved webset.
        """
        params = {"expand": expand} if expand else {}
        response = self.request(f"/v0/websets/{id}", params=params, method="GET", **extra)
        return GetWebsetResponse.model_validate(response)

    def list(self, *, cursor: Optional[str] = None, limit: Optional[int] = None, **extra: Unpack[ExtraRequestOptions]) -> ListWebsetsResponse:
        """List all Websets.
        
        Args:
            cursor (str, optional): The cursor to paginate through the results.
            limit (int, optional): The number of results to return (max 200).
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).
        
        Returns:
            ListWebsetsResponse: List of websets.
        """
        params = {k: v for k, v in {"cursor": cursor, "limit": limit}.items() if v is not None}
        response = self.request("/v0/websets", params=params, method="GET", **extra)
        return ListWebsetsResponse.model_validate(response)

    def update(self, id: str, params: Union[Dict[str, Any], UpdateWebsetRequest], **extra: Unpack[ExtraRequestOptions]) -> Webset:
        """Update a Webset.
        
        Args:
            id (str): The id or externalId of the Webset.
            params (UpdateWebsetRequest): The parameters for updating a webset.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).
        
        Returns:
            Webset: The updated webset.
        """
        response = self.request(f"/v0/websets/{id}", data=params, method="POST", **extra)
        return Webset.model_validate(response)

    def delete(self, id: str, **extra: Unpack[ExtraRequestOptions]) -> Webset:
        """Delete a Webset.
        
        Args:
            id (str): The id or externalId of the Webset.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).
        
        Returns:
            Webset: The deleted webset.
        """
        response = self.request(f"/v0/websets/{id}", method="DELETE", **extra)
        return Webset.model_validate(response)

    def cancel(self, id: str, **extra: Unpack[ExtraRequestOptions]) -> Webset:
        """Cancel a running Webset.
        
        Args:
            id (str): The id or externalId of the Webset.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).
        
        Returns:
            Webset: The canceled webset.
        """
        response = self.request(f"/v0/websets/{id}/cancel", method="POST", **extra)
        return Webset.model_validate(response)

    def list_all(self, *, limit: Optional[int] = None, **extra: Unpack[ExtraRequestOptions]) -> Iterator[Webset]:
        """Iterate through all Websets, handling pagination automatically.
        
        Args:
            limit (int, optional): The number of results to return per page (max 200).
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).
            
        Yields:
            Webset: Each webset.
        """
        cursor = None
        while True:
            response = self.list(cursor=cursor, limit=limit, **extra)
            for webset in response.data:
                yield webset
            
            if not response.has_more or not response.next_cursor:
                break
                
            cursor = response.next_cursor
            extra = options_for_next_page(extra)

    def get_all(self, *, limit: Optional[int] = None, **extra: Unpack[ExtraRequestOptions]) -> List[Webset]:
        """Collect all Websets into a list.
        
        Args:
            limit (int, optional): The number of results to return per page (max 200).
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).
            
        Returns:
            List[Webset]: All websets.
        """
        return list(self.list_all(limit=limit, **extra))

    def wait_until_idle(
        self, 
        id: str, 
        *, 
        timeout: int = 3600, 
        poll_interval: int = 5,
        on_poll: Optional[Callable[[Webset], None]] = None,
        **extra: Unpack[ExtraRequestOptions],
    ) -> Webset:
        """Wait until a Webset is idle.
        
        Args:
            id (str): The id or externalId of the Webset.
            timeout (int, optional): Maximum time to wait in seconds. Defaults to 3600.
            poll_interval (int, optional): Time to wait between polls in seconds. Defaults to 5.
            on_poll (Callable[[Webset], None], optional): Callback function called on each poll with the current webset.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).
            
        Returns:
            Webset: The webset once it's idle.
            
        Raises:
            TimeoutError: If the webset does not become idle within the timeout period.
        """
        start_time = time.time()
        while True:
            webset = self.get(id, **extra)
            
            if on_poll:
                on_poll(webset)
            
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
                     options: Optional[Union[Dict[str, Any], RequestOptions]] = None, **extra: Unpack[ExtraRequestOptions]) -> Webset:
        """Create a new Webset.
        
        Args:
            params (CreateWebsetParameters): The parameters for creating a webset.
            options (RequestOptions, optional): Request options including priority and/or custom headers.
                Can specify priority as 'low', 'medium', or 'high'.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).
        
        Returns:
            Webset: The created webset.
        """
        response = await self.request("/v0/websets", data=params, options=options, **extra)
        return Webset.model_validate(response)

    async def preview(self, params: Union[Dict[str, Any], PreviewWebsetParameters], **extra: Unpack[ExtraRequestOptions]) -> PreviewWebsetResponse:
        """Preview a Webset before creating it.
        
        Args:
            params (PreviewWebsetParameters): The parameters for previewing a webset.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).
        
        Returns:
            PreviewWebsetResponse: The preview results.
        """
        response = await self.request("/v0/websets/preview", data=params, **extra)
        return PreviewWebsetResponse.model_validate(response)

    async def get(self, id: str, *, expand: Optional[List[Literal["items"]]] = None, **extra: Unpack[ExtraRequestOptions]) -> GetWebsetResponse:
        """Get a Webset by ID.
        
        Args:
            id (str): The id or externalId of the Webset.
            expand (List[Literal["items"]], optional): Expand items in the response.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).
        
        Returns:
            GetWebsetResponse: The retrieved webset.
        """
        params = {}
        if expand is not None:
            params["expand"] = expand

        response = await self.request(f"/v0/websets/{id}", params=params, method="GET", **extra)
        return GetWebsetResponse.model_validate(response)

    async def list(self, *, cursor: Optional[str] = None, limit: Optional[int] = None, **extra: Unpack[ExtraRequestOptions]) -> ListWebsetsResponse:
        """List all Websets.
        
        Args:
            cursor (str, optional): The cursor to paginate through the results.
            limit (int, optional): The number of results to return (max 200).
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).
        
        Returns:
            ListWebsetsResponse: List of websets.
        """
        params = {k: v for k, v in {"cursor": cursor, "limit": limit}.items() if v is not None}
        response = await self.request("/v0/websets", params=params, method="GET", **extra)
        return ListWebsetsResponse.model_validate(response)

    async def update(self, id: str, params: Union[Dict[str, Any], UpdateWebsetRequest], **extra: Unpack[ExtraRequestOptions]) -> Webset:
        """Update a Webset.
        
        Args:
            id (str): The id or externalId of the Webset.
            params (UpdateWebsetRequest): The parameters for updating a webset.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).
        
        Returns:
            Webset: The updated webset.
        """
        response = await self.request(f"/v0/websets/{id}", data=params, method="POST", **extra)
        return Webset.model_validate(response)

    async def delete(self, id: str, **extra: Unpack[ExtraRequestOptions]) -> Webset:
        """Delete a Webset.
        
        Args:
            id (str): The id or externalId of the Webset.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).
        
        Returns:
            Webset: The deleted webset.
        """
        response = await self.request(f"/v0/websets/{id}", method="DELETE", **extra)
        return Webset.model_validate(response)

    async def cancel(self, id: str, **extra: Unpack[ExtraRequestOptions]) -> Webset:
        """Cancel a running Webset.
        
        Args:
            id (str): The id or externalId of the Webset.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).
        
        Returns:
            Webset: The canceled webset.
        """
        response = await self.request(f"/v0/websets/{id}/cancel", method="POST", **extra)
        return Webset.model_validate(response)

    async def list_all(self, *, limit: Optional[int] = None, **extra: Unpack[ExtraRequestOptions]) -> AsyncIterator[Webset]:
        """Iterate through all Websets, handling pagination automatically.
        
        Args:
            limit (int, optional): The number of results to return per page (max 200).
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).
            
        Yields:
            Webset: Each webset.
        """
        cursor = None
        while True:
            response = await self.list(cursor=cursor, limit=limit, **extra)
            for webset in response.data:
                yield webset
            
            if not response.has_more or not response.next_cursor:
                break
                
            cursor = response.next_cursor
            extra = options_for_next_page(extra)

    async def get_all(self, *, limit: Optional[int] = None, **extra: Unpack[ExtraRequestOptions]) -> List[Webset]:
        """Collect all Websets into a list.
        
        Args:
            limit (int, optional): The number of results to return per page (max 200).
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).
            
        Returns:
            List[Webset]: All websets.
        """
        websets = []
        async for webset in self.list_all(limit=limit, **extra):
            websets.append(webset)
        return websets

    async def wait_until_idle(
        self, 
        id: str, 
        *, 
        timeout: int = 3600, 
        poll_interval: int = 5,
        on_poll: Optional[Callable[[Webset], None]] = None,
        **extra: Unpack[ExtraRequestOptions],
    ) -> Webset:
        """Wait until a Webset is idle.
        
        Args:
            id (str): The id or externalId of the Webset.
            timeout (int, optional): Maximum time to wait in seconds. Defaults to 3600.
            poll_interval (int, optional): Time to wait between polls in seconds. Defaults to 5.
            on_poll (Callable[[Webset], None], optional): Callback function called on each poll with the current webset.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).
            
        Returns:
            Webset: The webset once it's idle.
            
        Raises:
            TimeoutError: If the webset does not become idle within the timeout period.
        """
        start_time = asyncio.get_event_loop().time()
        while True:
            webset = await self.get(id, **extra)
            
            if on_poll:
                on_poll(webset)
            
            if webset.status == WebsetStatus.idle.value:
                return webset
                
            if asyncio.get_event_loop().time() - start_time > timeout:
                raise TimeoutError(f"Webset {id} did not become idle within {timeout} seconds")
                
            await asyncio.sleep(poll_interval)
