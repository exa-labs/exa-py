from __future__ import annotations

from typing import Optional, Dict, Any, Union, Iterator, AsyncIterator, List

from ..types import (
    CreateWebhookParameters,
    Webhook,
    ListWebhooksResponse,
    UpdateWebhookParameters,
    ListWebhookAttemptsResponse,
    WebhookAttempt,
    EventType,
)
from ..core.base import WebsetsBaseClient
from ..core.async_base import WebsetsAsyncBaseClient

class WebhookAttemptsClient(WebsetsBaseClient):
    """Client for managing Webhook Attempts."""
    
    def __init__(self, client):
        super().__init__(client)
    
    def list(self, webhook_id: str, *, cursor: Optional[str] = None, 
             limit: Optional[int] = None, event_type: Optional[Union[EventType, str]] = None,
             successful: Optional[bool] = None) -> ListWebhookAttemptsResponse:
        """List all attempts made by a Webhook ordered in descending order.
        
        Args:
            webhook_id (str): The ID of the webhook.
            cursor (str, optional): The cursor to paginate through the results.
            limit (int, optional): The number of results to return (max 200).
            event_type (Union[EventType, str], optional): The type of event to filter by.
            successful (bool, optional): Filter attempts by success status.
        
        Returns:
            ListWebhookAttemptsResponse: List of webhook attempts.
        """
        event_type_value = None
        if event_type is not None:
            if isinstance(event_type, EventType):
                event_type_value = event_type.value
            else:
                event_type_value = event_type
                
        params = {k: v for k, v in {
            "cursor": cursor, 
            "limit": limit,
            "eventType": event_type_value,
            "successful": successful
        }.items() if v is not None}
        
        response = self.request(f"/v0/webhooks/{webhook_id}/attempts", params=params, method="GET")
        return ListWebhookAttemptsResponse.model_validate(response)

class WebsetWebhooksClient(WebsetsBaseClient):
    """Client for managing Webset Webhooks."""
    
    def __init__(self, client):
        super().__init__(client)
        self.attempts = WebhookAttemptsClient(client)

    def create(self, params: Union[Dict[str, Any], CreateWebhookParameters]) -> Webhook:
        """Create a Webhook.
        
        Args:
            params (CreateWebhookParameters): The parameters for creating a webhook.
        
        Returns:
            Webhook: The created webhook.
        """
        response = self.request("/v0/webhooks", data=params)
        return Webhook.model_validate(response)

    def get(self, id: str) -> Webhook:
        """Get a Webhook by ID.
        
        Args:
            id (str): The id of the webhook.
        
        Returns:
            Webhook: The retrieved webhook.
        """
        response = self.request(f"/v0/webhooks/{id}", method="GET")
        return Webhook.model_validate(response)

    def list(self, *, cursor: Optional[str] = None, limit: Optional[int] = None) -> ListWebhooksResponse:
        """List all Webhooks.
        
        Args:
            cursor (str, optional): The cursor to paginate through the results.
            limit (int, optional): The number of results to return (max 200).
        
        Returns:
            ListWebhooksResponse: List of webhooks.
        """
        params = {k: v for k, v in {"cursor": cursor, "limit": limit}.items() if v is not None}
        response = self.request("/v0/webhooks", params=params, method="GET")
        return ListWebhooksResponse.model_validate(response)

    def update(self, id: str, params: Union[Dict[str, Any], UpdateWebhookParameters]) -> Webhook:
        """Update a Webhook.
        
        Args:
            id (str): The id of the webhook.
            params (UpdateWebhookParameters): The parameters for updating a webhook.
        
        Returns:
            Webhook: The updated webhook.
        """
        response = self.request(f"/v0/webhooks/{id}", data=params, method="PATCH")
        return Webhook.model_validate(response)

    def delete(self, id: str) -> Webhook:
        """Delete a Webhook.
        
        Args:
            id (str): The id of the webhook.
        
        Returns:
            Webhook: The deleted webhook.
        """
        response = self.request(f"/v0/webhooks/{id}", method="DELETE")
        return Webhook.model_validate(response)

    def list_all(self, *, limit: Optional[int] = None) -> Iterator[Webhook]:
        """Iterate through all Webhooks, handling pagination automatically.
        
        Args:
            limit (int, optional): The number of results to return per page (max 200).
            
        Yields:
            Webhook: Each webhook.
        """
        cursor = None
        while True:
            response = self.list(cursor=cursor, limit=limit)
            for webhook in response.data:
                yield webhook
            
            if not response.has_more or not response.next_cursor:
                break
                
            cursor = response.next_cursor

    def get_all(self, *, limit: Optional[int] = None) -> List[Webhook]:
        """Collect all Webhooks into a list.
        
        Args:
            limit (int, optional): The number of results to return per page (max 200).
            
        Returns:
            List[Webhook]: All webhooks.
        """
        return list(self.list_all(limit=limit))

    def list_all_attempts(
        self, 
        webhook_id: str, 
        *, 
        limit: Optional[int] = None,
        event_type: Optional[Union[EventType, str]] = None,
        successful: Optional[bool] = None
    ) -> Iterator[WebhookAttempt]:
        """Iterate through all attempts for a Webhook, handling pagination automatically.
        
        Args:
            webhook_id (str): The ID of the webhook.
            limit (int, optional): The number of results to return per page (max 200).
            event_type (Union[EventType, str], optional): The type of event to filter by.
            successful (bool, optional): Filter attempts by success status.
            
        Yields:
            WebhookAttempt: Each webhook attempt.
        """
        cursor = None
        while True:
            response = self.attempts.list(
                webhook_id, 
                cursor=cursor, 
                limit=limit, 
                event_type=event_type, 
                successful=successful
            )
            for attempt in response.data:
                yield attempt
            
            if not response.has_more or not response.next_cursor:
                break
                
            cursor = response.next_cursor

    def get_all_attempts(
        self, 
        webhook_id: str, 
        *, 
        limit: Optional[int] = None,
        event_type: Optional[Union[EventType, str]] = None,
        successful: Optional[bool] = None
    ) -> List[WebhookAttempt]:
        """Collect all attempts for a Webhook into a list.
        
        Args:
            webhook_id (str): The ID of the webhook.
            limit (int, optional): The number of results to return per page (max 200).
            event_type (Union[EventType, str], optional): The type of event to filter by.
            successful (bool, optional): Filter attempts by success status.
            
        Returns:
            List[WebhookAttempt]: All webhook attempts.
        """
        return list(self.list_all_attempts(
            webhook_id, 
            limit=limit, 
            event_type=event_type, 
            successful=successful
        ))


class AsyncWebhookAttemptsClient(WebsetsAsyncBaseClient):
    """Async client for managing Webhook Attempts."""
    
    def __init__(self, client):
        super().__init__(client)
    
    async def list(self, webhook_id: str, *, cursor: Optional[str] = None, 
             limit: Optional[int] = None, event_type: Optional[Union[EventType, str]] = None,
             successful: Optional[bool] = None) -> ListWebhookAttemptsResponse:
        """List all attempts made by a Webhook ordered in descending order."""
        event_type_value = None
        if event_type is not None:
            if isinstance(event_type, EventType):
                event_type_value = event_type.value
            else:
                event_type_value = event_type
                
        params = {k: v for k, v in {
            "cursor": cursor, 
            "limit": limit,
            "eventType": event_type_value,
            "successful": successful
        }.items() if v is not None}
        
        response = await self.request(f"/v0/webhooks/{webhook_id}/attempts", params=params, method="GET")
        return ListWebhookAttemptsResponse.model_validate(response)

class AsyncWebsetWebhooksClient(WebsetsAsyncBaseClient):
    """Async client for managing Webset Webhooks."""
    
    def __init__(self, client):
        super().__init__(client)
        self.attempts = AsyncWebhookAttemptsClient(client)

    async def create(self, params: Union[Dict[str, Any], CreateWebhookParameters]) -> Webhook:
        """Create a Webhook."""
        response = await self.request("/v0/webhooks", data=params)
        return Webhook.model_validate(response)

    async def get(self, id: str) -> Webhook:
        """Get a Webhook by ID."""
        response = await self.request(f"/v0/webhooks/{id}", method="GET")
        return Webhook.model_validate(response)

    async def list(self, *, cursor: Optional[str] = None, limit: Optional[int] = None) -> ListWebhooksResponse:
        """List all Webhooks."""
        params = {k: v for k, v in {"cursor": cursor, "limit": limit}.items() if v is not None}
        response = await self.request("/v0/webhooks", params=params, method="GET")
        return ListWebhooksResponse.model_validate(response)

    async def update(self, id: str, params: Union[Dict[str, Any], UpdateWebhookParameters]) -> Webhook:
        """Update a Webhook."""
        response = await self.request(f"/v0/webhooks/{id}", data=params, method="PATCH")
        return Webhook.model_validate(response)

    async def delete(self, id: str) -> Webhook:
        """Delete a Webhook."""
        response = await self.request(f"/v0/webhooks/{id}", method="DELETE")
        return Webhook.model_validate(response)

    async def list_all(self, *, limit: Optional[int] = None) -> AsyncIterator[Webhook]:
        """Iterate through all Webhooks, handling pagination automatically.
        
        Args:
            limit (int, optional): The number of results to return per page (max 200).
            
        Yields:
            Webhook: Each webhook.
        """
        cursor = None
        while True:
            response = await self.list(cursor=cursor, limit=limit)
            for webhook in response.data:
                yield webhook
            
            if not response.has_more or not response.next_cursor:
                break
                
            cursor = response.next_cursor

    async def get_all(self, *, limit: Optional[int] = None) -> List[Webhook]:
        """Collect all Webhooks into a list.
        
        Args:
            limit (int, optional): The number of results to return per page (max 200).
            
        Returns:
            List[Webhook]: All webhooks.
        """
        webhooks = []
        async for webhook in self.list_all(limit=limit):
            webhooks.append(webhook)
        return webhooks

    async def list_all_attempts(
        self, 
        webhook_id: str, 
        *, 
        limit: Optional[int] = None,
        event_type: Optional[Union[EventType, str]] = None,
        successful: Optional[bool] = None
    ) -> AsyncIterator[WebhookAttempt]:
        """Iterate through all attempts for a Webhook, handling pagination automatically.
        
        Args:
            webhook_id (str): The ID of the webhook.
            limit (int, optional): The number of results to return per page (max 200).
            event_type (Union[EventType, str], optional): The type of event to filter by.
            successful (bool, optional): Filter attempts by success status.
            
        Yields:
            WebhookAttempt: Each webhook attempt.
        """
        cursor = None
        while True:
            response = await self.attempts.list(
                webhook_id, 
                cursor=cursor, 
                limit=limit, 
                event_type=event_type, 
                successful=successful
            )
            for attempt in response.data:
                yield attempt
            
            if not response.has_more or not response.next_cursor:
                break
                
            cursor = response.next_cursor

    async def get_all_attempts(
        self, 
        webhook_id: str, 
        *, 
        limit: Optional[int] = None,
        event_type: Optional[Union[EventType, str]] = None,
        successful: Optional[bool] = None
    ) -> List[WebhookAttempt]:
        """Collect all attempts for a Webhook into a list.
        
        Args:
            webhook_id (str): The ID of the webhook.
            limit (int, optional): The number of results to return per page (max 200).
            event_type (Union[EventType, str], optional): The type of event to filter by.
            successful (bool, optional): Filter attempts by success status.
            
        Returns:
            List[WebhookAttempt]: All webhook attempts.
        """
        attempts = []
        async for attempt in self.list_all_attempts(
            webhook_id, 
            limit=limit, 
            event_type=event_type, 
            successful=successful
        ):
            attempts.append(attempt)
        return attempts
