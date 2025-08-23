from __future__ import annotations

import time
import os
import csv
import io
import asyncio
import requests
import httpx
from typing import Dict, Any, Union, Optional
from pathlib import Path

from ..types import (
    CreateImportParameters,
    CreateImportResponse,
    Import,
    ListImportsResponse,
    UpdateImport,
)
from ..core.base import WebsetsBaseClient
from ..core.async_base import WebsetsAsyncBaseClient

class ImportsClient(WebsetsBaseClient):
    """Client for managing Imports."""
    
    def __init__(self, client):
        super().__init__(client)

    def create(
        self, 
        params: Union[Dict[str, Any], CreateImportParameters], 
        *,
        csv_data: Optional[Union[str, Path]] = None
    ) -> Union[CreateImportResponse, Import]:
        """Create a new import to upload your data into Websets.
        
        Imports can be used to:
        - Enrich: Enhance your data with additional information using our AI-powered enrichment engine
        - Search: Query your data using Websets' agentic search with natural language filters
        - Exclude: Prevent duplicate or already known results from appearing in your searches

        Args:
            params (CreateImportParameters): The parameters for creating an import.
            csv_data (Union[str, Path], optional): CSV data to upload. Can be raw CSV string or file path.
                                                   When provided, size and count will be automatically calculated 
                                                   if not specified in params.
        
        Returns:
            CreateImportResponse: If csv_data is None (traditional usage with upload URL).
            Import: If csv_data is provided (uploaded and processing).
        """
        if csv_data is not None:
            if isinstance(csv_data, (str, Path)) and os.path.isfile(csv_data):
                with open(csv_data, 'r', encoding='utf-8') as f:
                    csv_content = f.read()
            else:
                csv_content = str(csv_data)
            
            if isinstance(params, dict):
                current_size = params.get('size')
                current_count = params.get('count')
            else:
                current_size = getattr(params, 'size', None)
                current_count = getattr(params, 'count', None)
            
            if current_size is None or current_count is None:
                calculated_size = len(csv_content.encode('utf-8'))
                csv_reader = csv.reader(io.StringIO(csv_content))
                rows = list(csv_reader)
                calculated_count = max(0, len(rows) - 1)
                
                if isinstance(params, dict):
                    params = params.copy()
                    if current_size is None:
                        params['size'] = calculated_size
                    if current_count is None:
                        params['count'] = calculated_count
                else:
                    params_dict = params.model_dump()
                    if current_size is None:
                        params_dict['size'] = calculated_size
                    if current_count is None:
                        params_dict['count'] = calculated_count
                    params = CreateImportParameters.model_validate(params_dict)
        
        response = self.request("/v0/imports", data=params)
        import_response = CreateImportResponse.model_validate(response)
        
        if csv_data is None:
            return import_response
        
        upload_response = requests.put(
            import_response.upload_url,
            data=csv_content,
            headers={'Content-Type': 'text/csv'}
        )
        upload_response.raise_for_status()
        
        return self.get(import_response.id)

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


class AsyncImportsClient(WebsetsAsyncBaseClient):
    """Async client for managing Imports."""
    
    def __init__(self, client):
        super().__init__(client)

    async def create(
        self, 
        params: Union[Dict[str, Any], CreateImportParameters], 
        *,
        csv_data: Optional[Union[str, Path]] = None
    ) -> Union[CreateImportResponse, Import]:
        """Create a new import to upload your data into Websets.
        
        Imports can be used to:
        - Enrich: Enhance your data with additional information using our AI-powered enrichment engine
        - Search: Query your data using Websets' agentic search with natural language filters
        - Exclude: Prevent duplicate or already known results from appearing in your searches

        Args:
            params (CreateImportParameters): The parameters for creating an import.
            csv_data (Union[str, Path], optional): CSV data to upload. Can be raw CSV string or file path.
                                                   When provided, size and count will be automatically calculated 
                                                   if not specified in params.
        
        Returns:
            CreateImportResponse: If csv_data is None (traditional usage with upload URL).
            Import: If csv_data is provided (uploaded and processing).
        """
        if csv_data is not None:
            if isinstance(csv_data, (str, Path)) and os.path.isfile(csv_data):
                # Use synchronous file reading for simplicity (file reading is typically fast)
                with open(csv_data, 'r', encoding='utf-8') as f:
                    csv_content = f.read()
            else:
                csv_content = str(csv_data)
            
            if isinstance(params, dict):
                current_size = params.get('size')
                current_count = params.get('count')
            else:
                current_size = getattr(params, 'size', None)
                current_count = getattr(params, 'count', None)
            
            if current_size is None or current_count is None:
                calculated_size = len(csv_content.encode('utf-8'))
                csv_reader = csv.reader(io.StringIO(csv_content))
                rows = list(csv_reader)
                calculated_count = max(0, len(rows) - 1)
                
                if isinstance(params, dict):
                    params = params.copy()
                    if current_size is None:
                        params['size'] = calculated_size
                    if current_count is None:
                        params['count'] = calculated_count
                else:
                    params_dict = params.model_dump()
                    if current_size is None:
                        params_dict['size'] = calculated_size
                    if current_count is None:
                        params_dict['count'] = calculated_count
                    params = CreateImportParameters.model_validate(params_dict)
        
        response = await self.request("/v0/imports", data=params)
        import_response = CreateImportResponse.model_validate(response)
        
        if csv_data is None:
            return import_response
        
        # Use httpx for async HTTP requests
        async with httpx.AsyncClient() as http_client:
            upload_response = await http_client.put(
                import_response.upload_url,
                data=csv_content,
                headers={'Content-Type': 'text/csv'}
            )
            upload_response.raise_for_status()
        
        return await self.get(import_response.id)

    async def get(self, import_id: str) -> Import:
        """Get a specific import.
        
        Args:
            import_id (str): The id of the Import.
        
        Returns:
            Import: The retrieved import.
        """
        response = await self.request(f"/v0/imports/{import_id}", method="GET")
        return Import.model_validate(response)

    async def list(self, *, cursor: Optional[str] = None, limit: Optional[int] = None) -> ListImportsResponse:
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
        response = await self.request("/v0/imports", params=params, method="GET")
        return ListImportsResponse.model_validate(response)

    async def update(self, import_id: str, params: Union[Dict[str, Any], UpdateImport]) -> Import:
        """Update an import configuration.
        
        Args:
            import_id (str): The id of the Import.
            params (UpdateImport): The parameters for updating an import.
        
        Returns:
            Import: The updated import.
        """
        response = await self.request(f"/v0/imports/{import_id}", data=params, method="PATCH")
        return Import.model_validate(response)

    async def delete(self, import_id: str) -> Import:
        """Delete an import.
        
        Args:
            import_id (str): The id of the Import.
        
        Returns:
            Import: The deleted import.
        """
        response = await self.request(f"/v0/imports/{import_id}", method="DELETE")
        return Import.model_validate(response)

    async def wait_until_completed(self, import_id: str, *, timeout: int = 1800, poll_interval: int = 5) -> Import:
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
        start_time = asyncio.get_event_loop().time()
        while True:
            import_obj = await self.get(import_id)
            if import_obj.status in ['completed', 'failed']:
                return import_obj
                
            if asyncio.get_event_loop().time() - start_time > timeout:
                raise TimeoutError(f"Import {import_id} did not complete within {timeout} seconds")
                
            await asyncio.sleep(poll_interval) 