from __future__ import annotations

from typing import Dict, Any, Union

from ..types import (
    CreateEnrichmentParameters,
    WebsetEnrichment,
)
from ..core.base import WebsetsBaseClient

class WebsetEnrichmentsClient(WebsetsBaseClient):
    """Client for managing Webset Enrichments."""
    
    def __init__(self, client):
        super().__init__(client)

    def create(self, webset_id: str, params: Union[Dict[str, Any], CreateEnrichmentParameters]) -> WebsetEnrichment:
        """Create an Enrichment for a Webset.
        
        Args:
            webset_id (str): The id of the Webset.
            params (CreateEnrichmentParameters): The parameters for creating an enrichment.
        
        Returns:
            WebsetEnrichment: The created enrichment.
        """
        response = self.request(f"/v0/websets/{webset_id}/enrichments", data=params)
        return WebsetEnrichment.model_validate(response)

    def get(self, webset_id: str, id: str) -> WebsetEnrichment:
        """Get an Enrichment by ID.
        
        Args:
            webset_id (str): The id of the Webset.
            id (str): The id of the Enrichment.
        
        Returns:
            WebsetEnrichment: The retrieved enrichment.
        """
        response = self.request(f"/v0/websets/{webset_id}/enrichments/{id}", method="GET")
        return WebsetEnrichment.model_validate(response)

    def delete(self, webset_id: str, id: str) -> WebsetEnrichment:
        """Delete an Enrichment.
        
        Args:
            webset_id (str): The id of the Webset.
            id (str): The id of the Enrichment.
        
        Returns:
            WebsetEnrichment: The deleted enrichment.
        """
        response = self.request(f"/v0/websets/{webset_id}/enrichments/{id}", method="DELETE")
        return WebsetEnrichment.model_validate(response)

    def cancel(self, webset_id: str, id: str) -> WebsetEnrichment:
        """Cancel a running Enrichment.
        
        Args:
            webset_id (str): The id of the Webset.
            id (str): The id of the Enrichment.
        
        Returns:
            WebsetEnrichment: The canceled enrichment.
        """
        response = self.request(f"/v0/websets/{webset_id}/enrichments/{id}/cancel", method="POST")
        return WebsetEnrichment.model_validate(response) 