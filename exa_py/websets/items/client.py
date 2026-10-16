from __future__ import annotations

from typing import Optional, Iterator, AsyncIterator, List
from typing_extensions import Unpack

from ..types import (
    WebsetItem,
    ListWebsetItemResponse,
)
from ..core.base import WebsetsBaseClient
from ..core.async_base import WebsetsAsyncBaseClient
from ...request_options import ExtraRequestOptions, options_for_next_page

class WebsetItemsClient(WebsetsBaseClient):
    """Client for managing Webset Items."""
    
    def __init__(self, client):
        super().__init__(client)

    def list(self, webset_id: str, *, cursor: Optional[str] = None, 
             limit: Optional[int] = None, source_id: Optional[str] = None, **extra: Unpack[ExtraRequestOptions]) -> ListWebsetItemResponse:
        """List all Items for a Webset.
        
        Args:
            webset_id (str): The id or externalId of the Webset.
            cursor (str, optional): The cursor to paginate through the results.
            limit (int, optional): The number of results to return (max 200).
            source_id (str, optional): Filter items by source ID.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).
        
        Returns:
            ListWebsetItemResponse: List of webset items.
        """
        params = {k: v for k, v in {"cursor": cursor, "limit": limit, "sourceId": source_id}.items() if v is not None}
        response = self.request(f"/v0/websets/{webset_id}/items", params=params, method="GET", **extra)
        return ListWebsetItemResponse.model_validate(response)

    def list_all(self, webset_id: str, *, limit: Optional[int] = None, source_id: Optional[str] = None, **extra: Unpack[ExtraRequestOptions]) -> Iterator[WebsetItem]:
        """Iterate through all Items in a Webset, handling pagination automatically.
        
        Args:
            webset_id (str): The id or externalId of the Webset.
            limit (int, optional): The number of results to return per page (max 200).
            source_id (str, optional): Filter items by source ID.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).
            
        Yields:
            WebsetItem: Each item in the webset.
        """
        cursor = None
        while True:
            response = self.list(webset_id, cursor=cursor, limit=limit, source_id=source_id, **extra)
            for item in response.data:
                yield item
            
            if not response.has_more or not response.next_cursor:
                break
                
            cursor = response.next_cursor
            extra = options_for_next_page(extra)

    def get_all(self, webset_id: str, *, limit: Optional[int] = None, source_id: Optional[str] = None, **extra: Unpack[ExtraRequestOptions]) -> List[WebsetItem]:
        """Collect all Items from a Webset into a list.
        
        Args:
            webset_id (str): The id or externalId of the Webset.
            limit (int, optional): The number of results to return per page (max 200).
            source_id (str, optional): Filter items by source ID.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).
            
        Returns:
            List[WebsetItem]: All items in the webset.
        """
        return list(self.list_all(webset_id, limit=limit, source_id=source_id, **extra))

    def get(self, webset_id: str, id: str, **extra: Unpack[ExtraRequestOptions]) -> WebsetItem:
        """Get an Item by ID.
        
        Args:
            webset_id (str): The id or externalId of the Webset.
            id (str): The id of the Webset item.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).
        
        Returns:
            WebsetItem: The retrieved item.
        """
        response = self.request(f"/v0/websets/{webset_id}/items/{id}", method="GET", **extra)
        return WebsetItem.model_validate(response)

    def delete(self, webset_id: str, id: str, **extra: Unpack[ExtraRequestOptions]) -> WebsetItem:
        """Delete an Item.
        
        Args:
            webset_id (str): The id or externalId of the Webset.
            id (str): The id of the Webset item.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).
        
        Returns:
            WebsetItem: The deleted item.
        """
        response = self.request(f"/v0/websets/{webset_id}/items/{id}", method="DELETE", **extra)
        return WebsetItem.model_validate(response)


class AsyncWebsetItemsClient(WebsetsAsyncBaseClient):
    """Async client for managing Webset Items."""
    
    def __init__(self, client):
        super().__init__(client)

    async def list(self, webset_id: str, *, cursor: Optional[str] = None, 
             limit: Optional[int] = None, source_id: Optional[str] = None, **extra: Unpack[ExtraRequestOptions]) -> ListWebsetItemResponse:
        """List all Items for a Webset.
        
        Args:
            webset_id (str): The id or externalId of the Webset.
            cursor (str, optional): The cursor to paginate through the results.
            limit (int, optional): The number of results to return (max 200).
            source_id (str, optional): Filter items by source ID.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).
        
        Returns:
            ListWebsetItemResponse: List of webset items.
        """
        params = {k: v for k, v in {"cursor": cursor, "limit": limit, "sourceId": source_id}.items() if v is not None}
        response = await self.request(f"/v0/websets/{webset_id}/items", params=params, method="GET", **extra)
        return ListWebsetItemResponse.model_validate(response)

    async def list_all(self, webset_id: str, *, limit: Optional[int] = None, source_id: Optional[str] = None, **extra: Unpack[ExtraRequestOptions]) -> AsyncIterator[WebsetItem]:
        """Iterate through all Items in a Webset, handling pagination automatically.
        
        Args:
            webset_id (str): The id or externalId of the Webset.
            limit (int, optional): The number of results to return per page (max 200).
            source_id (str, optional): Filter items by source ID.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).
            
        Yields:
            WebsetItem: Each item in the webset.
        """
        cursor = None
        while True:
            response = await self.list(webset_id, cursor=cursor, limit=limit, source_id=source_id, **extra)
            for item in response.data:
                yield item
            
            if not response.has_more or not response.next_cursor:
                break
                
            cursor = response.next_cursor
            extra = options_for_next_page(extra)

    async def get_all(self, webset_id: str, *, limit: Optional[int] = None, source_id: Optional[str] = None, **extra: Unpack[ExtraRequestOptions]) -> List[WebsetItem]:
        """Collect all Items from a Webset into a list.
        
        Args:
            webset_id (str): The id or externalId of the Webset.
            limit (int, optional): The number of results to return per page (max 200).
            source_id (str, optional): Filter items by source ID.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).
            
        Returns:
            List[WebsetItem]: All items in the webset.
        """
        items = []
        async for item in self.list_all(webset_id, limit=limit, source_id=source_id, **extra):
            items.append(item)
        return items

    async def get(self, webset_id: str, id: str, **extra: Unpack[ExtraRequestOptions]) -> WebsetItem:
        """Get an Item by ID.
        
        Args:
            webset_id (str): The id or externalId of the Webset.
            id (str): The id of the Webset item.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).
        
        Returns:
            WebsetItem: The retrieved item.
        """
        response = await self.request(f"/v0/websets/{webset_id}/items/{id}", method="GET", **extra)
        return WebsetItem.model_validate(response)

    async def delete(self, webset_id: str, id: str, **extra: Unpack[ExtraRequestOptions]) -> WebsetItem:
        """Delete an Item.
        
        Args:
            webset_id (str): The id or externalId of the Webset.
            id (str): The id of the Webset item.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).
        
        Returns:
            WebsetItem: The deleted item.
        """
        response = await self.request(f"/v0/websets/{webset_id}/items/{id}", method="DELETE", **extra)
        return WebsetItem.model_validate(response)      