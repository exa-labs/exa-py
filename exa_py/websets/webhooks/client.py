from __future__ import annotations

from typing import Optional, Dict, Any, Union, Literal

from ..types import (
    CreateWebhookParameters,
    Webhook,
    ListWebhooksResponse,
    UpdateWebhookParameters,
    ListWebhookAttemptsResponse,
    EventType,
)
from ..core.base import WebsetsBaseClient

class WebhookAttemptsClient(WebsetsBaseClient):
    """Client for managing Webhook Attempts."""
    
    def __init__(self, client):
        super().__init__(client)
    
    def list(self, webhook_id: str, *, cursor: Optional[str] = None, 
             limit: Optional[int] = None, event_type: Optional[Union[EventType, str]] = None) -> ListWebhookAttemptsResponse:
        """List all attempts made by a Webhook ordered in descending order.
        
        Args:
            webhook_id (str): The ID of the webhook.
            cursor (str, optional): The cursor to paginate through the results.
            limit (int, optional): The number of results to return (max 200).
            event_type (Union[EventType, str], optional): The type of event to filter by.
        
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
            "eventType": event_type_value
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