from __future__ import annotations

from typing import Optional

from ..types import (
    CreateWebhookParameters,
    Webhook,
    ListWebhooksResponse,
    UpdateWebhookParameters,
)
from ..core.base import WebsetsBaseClient

class WebsetWebhooksClient(WebsetsBaseClient):
    """Client for managing Webset Webhooks."""
    
    def __init__(self, client):
        super().__init__(client)

    def create(self, params: CreateWebhookParameters) -> Webhook:
        """Create a Webhook.
        
        Args:
            params (CreateWebhookParameters): The parameters for creating a webhook.
        
        Returns:
            Webhook: The created webhook.
        """
        response = self.request("/v0/webhooks", data=params.model_dump(by_alias=True, exclude_none=True))
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

    def update(self, id: str, params: UpdateWebhookParameters) -> Webhook:
        """Update a Webhook.
        
        Args:
            id (str): The id of the webhook.
            params (UpdateWebhookParameters): The parameters for updating a webhook.
        
        Returns:
            Webhook: The updated webhook.
        """
        response = self.request(f"/v0/webhooks/{id}", data=params.model_dump(by_alias=True, exclude_none=True), method="PATCH")
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