from __future__ import annotations

from typing import Dict, Any, Union
from typing_extensions import Unpack

from ..types import (
    CreateEnrichmentParameters,
    UpdateEnrichmentParameters,
    WebsetEnrichment,
)
from ..core.base import WebsetsBaseClient
from ..core.async_base import WebsetsAsyncBaseClient
from ...request_options import ExtraRequestOptions

class WebsetEnrichmentsClient(WebsetsBaseClient):
    """Client for managing Webset Enrichments."""
    
    def __init__(self, client):
        super().__init__(client)

    def create(self, webset_id: str, params: Union[Dict[str, Any], CreateEnrichmentParameters], **extra: Unpack[ExtraRequestOptions]) -> WebsetEnrichment:
        """Create an Enrichment for a Webset.
        
        Args:
            webset_id (str): The id of the Webset.
            params (CreateEnrichmentParameters): The parameters for creating an enrichment.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).
        
        Returns:
            WebsetEnrichment: The created enrichment.
        """
        response = self.request(f"/v0/websets/{webset_id}/enrichments", data=params, **extra)
        return WebsetEnrichment.model_validate(response)

    def get(self, webset_id: str, id: str, **extra: Unpack[ExtraRequestOptions]) -> WebsetEnrichment:
        """Get an Enrichment by ID.
        
        Args:
            webset_id (str): The id of the Webset.
            id (str): The id of the Enrichment.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).
        
        Returns:
            WebsetEnrichment: The retrieved enrichment.
        """
        response = self.request(f"/v0/websets/{webset_id}/enrichments/{id}", method="GET", **extra)
        return WebsetEnrichment.model_validate(response)

    def update(self, webset_id: str, id: str, params: Union[Dict[str, Any], UpdateEnrichmentParameters], **extra: Unpack[ExtraRequestOptions]) -> WebsetEnrichment:
        """Update an Enrichment.
        
        Args:
            webset_id (str): The id of the Webset.
            id (str): The id of the Enrichment.
            params (UpdateEnrichmentParameters): The parameters for updating an enrichment.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).
        
        Returns:
            WebsetEnrichment: The updated enrichment.
        """
        response = self.request(f"/v0/websets/{webset_id}/enrichments/{id}", data=params, method="PATCH", **extra)
        return WebsetEnrichment.model_validate(response)

    def delete(self, webset_id: str, id: str, **extra: Unpack[ExtraRequestOptions]) -> WebsetEnrichment:
        """Delete an Enrichment.
        
        Args:
            webset_id (str): The id of the Webset.
            id (str): The id of the Enrichment.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).
        
        Returns:
            WebsetEnrichment: The deleted enrichment.
        """
        response = self.request(f"/v0/websets/{webset_id}/enrichments/{id}", method="DELETE", **extra)
        return WebsetEnrichment.model_validate(response)

    def cancel(self, webset_id: str, id: str, **extra: Unpack[ExtraRequestOptions]) -> WebsetEnrichment:
        """Cancel a running Enrichment.
        
        Args:
            webset_id (str): The id of the Webset.
            id (str): The id of the Enrichment.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).
        
        Returns:
            WebsetEnrichment: The canceled enrichment.
        """
        response = self.request(f"/v0/websets/{webset_id}/enrichments/{id}/cancel", method="POST", **extra)
        return WebsetEnrichment.model_validate(response)


class AsyncWebsetEnrichmentsClient(WebsetsAsyncBaseClient):
    """Async client for managing Webset Enrichments."""
    
    def __init__(self, client):
        super().__init__(client)

    async def create(self, webset_id: str, params: Union[Dict[str, Any], CreateEnrichmentParameters], **extra: Unpack[ExtraRequestOptions]) -> WebsetEnrichment:
        """Create an Enrichment for a Webset.
        
        Args:
            webset_id (str): The id of the Webset.
            params (CreateEnrichmentParameters): The parameters for creating an enrichment.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).
        
        Returns:
            WebsetEnrichment: The created enrichment.
        """
        response = await self.request(f"/v0/websets/{webset_id}/enrichments", data=params, **extra)
        return WebsetEnrichment.model_validate(response)

    async def get(self, webset_id: str, id: str, **extra: Unpack[ExtraRequestOptions]) -> WebsetEnrichment:
        """Get an Enrichment by ID.
        
        Args:
            webset_id (str): The id of the Webset.
            id (str): The id of the Enrichment.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).
        
        Returns:
            WebsetEnrichment: The retrieved enrichment.
        """
        response = await self.request(f"/v0/websets/{webset_id}/enrichments/{id}", method="GET", **extra)
        return WebsetEnrichment.model_validate(response)

    async def update(self, webset_id: str, id: str, params: Union[Dict[str, Any], UpdateEnrichmentParameters], **extra: Unpack[ExtraRequestOptions]) -> WebsetEnrichment:
        """Update an Enrichment.
        
        Args:
            webset_id (str): The id of the Webset.
            id (str): The id of the Enrichment.
            params (UpdateEnrichmentParameters): The parameters for updating an enrichment.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).
        
        Returns:
            WebsetEnrichment: The updated enrichment.
        """
        response = await self.request(f"/v0/websets/{webset_id}/enrichments/{id}", data=params, method="PATCH", **extra)
        return WebsetEnrichment.model_validate(response)

    async def delete(self, webset_id: str, id: str, **extra: Unpack[ExtraRequestOptions]) -> WebsetEnrichment:
        """Delete an Enrichment.
        
        Args:
            webset_id (str): The id of the Webset.
            id (str): The id of the Enrichment.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).
        
        Returns:
            WebsetEnrichment: The deleted enrichment.
        """
        response = await self.request(f"/v0/websets/{webset_id}/enrichments/{id}", method="DELETE", **extra)
        return WebsetEnrichment.model_validate(response)

    async def cancel(self, webset_id: str, id: str, **extra: Unpack[ExtraRequestOptions]) -> WebsetEnrichment:
        """Cancel a running Enrichment.
        
        Args:
            webset_id (str): The id of the Webset.
            id (str): The id of the Enrichment.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).
        
        Returns:
            WebsetEnrichment: The canceled enrichment.
        """
        response = await self.request(f"/v0/websets/{webset_id}/enrichments/{id}/cancel", method="POST", **extra)
        return WebsetEnrichment.model_validate(response) 