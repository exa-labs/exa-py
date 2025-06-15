from __future__ import annotations

import time
from typing import Dict, Any, Union, Optional

from ..types import (
    CreateImportParameters,
    CreateImportResponse,
    Import,
    ListImportsResponse,
    UpdateImport,
    ImportStatus,
)
from ..core.base import WebsetsBaseClient

class ImportsClient(WebsetsBaseClient):
    """Client for managing Imports."""
    
    def __init__(self, client):
        super().__init__(client)

    def create(self, params: Union[Dict[str, Any], CreateImportParameters]) -> CreateImportResponse:
        """Create a new import to upload your data into Websets.
        
        Imports can be used to:
        - Enrich: Enhance your data with additional information using our AI-powered enrichment engine
        - Search: Query your data using Websets' agentic search with natural language filters
        - Exclude: Prevent duplicate or already known results from appearing in your searches

        Once the import is created, you can upload your data to the returned uploadUrl until uploadValidUntil (by default 1 hour).
        
        Args:
            params (CreateImportParameters): The parameters for creating an import.
        
        Returns:
            CreateImportResponse: The created import with upload URL.
        """
        response = self.request("/v0/imports", data=params)
        return CreateImportResponse.model_validate(response)

    def get(self, import_id: str) -> Import:
        """Get a specific import.
        
        Args:
            import_id (str): The id of the Import.
        
        Returns:
            Import: The retrieved import.
        """
        response = self.request(f"/v0/imports/{import_id}", method="GET")
        return Import.model_validate(response)

    def list(self, *, cursor: Optional[str] = None, limit: Optional[int] = None) -> ListImportsResponse:
        """List all imports.
        
        Args:
            cursor (str, optional): The cursor to paginate through the results.
            limit (int, optional): The number of results to return (1-200, default 25).
        
        Returns:
            ListImportsResponse: List of imports with pagination info.
        """
        params = {
            k: v 
            for k, v in {
                "cursor": cursor, 
                "limit": limit
            }.items() 
            if v is not None
        }
        response = self.request("/v0/imports", params=params, method="GET")
        return ListImportsResponse.model_validate(response)

    def update(self, import_id: str, params: Union[Dict[str, Any], UpdateImport]) -> Import:
        """Update an import configuration.
        
        Args:
            import_id (str): The id of the Import.
            params (UpdateImport): The parameters for updating an import.
        
        Returns:
            Import: The updated import.
        """
        response = self.request(f"/v0/imports/{import_id}", data=params, method="PATCH")
        return Import.model_validate(response)

    def delete(self, import_id: str) -> Import:
        """Delete an import.
        
        Args:
            import_id (str): The id of the Import.
        
        Returns:
            Import: The deleted import.
        """
        response = self.request(f"/v0/imports/{import_id}", method="DELETE")
        return Import.model_validate(response)

    def wait_until_completed(self, import_id: str, *, timeout: int = 1800, poll_interval: int = 5) -> Import:
        """Wait until an import is completed or failed.
        
        Args:
            import_id (str): The id of the Import.
            timeout (int, optional): Maximum time to wait in seconds. Defaults to 1800 (30 minutes).
            poll_interval (int, optional): Time to wait between polls in seconds. Defaults to 5.
            
        Returns:
            Import: The import once it's completed or failed.
            
        Raises:
            TimeoutError: If the import does not complete within the timeout period.
        """
        start_time = time.time()
        while True:
            import_obj = self.get(import_id)
            if import_obj.status in ['completed', 'failed']:
                return import_obj
                
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Import {import_id} did not complete within {timeout} seconds")
                
            time.sleep(poll_interval) 