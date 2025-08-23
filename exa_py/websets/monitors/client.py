from __future__ import annotations

from typing import Dict, Any, Union, Optional

from ..types import (
    Monitor,
    CreateMonitorParameters,
    UpdateMonitor,
    ListMonitorsResponse,
)
from ..core.base import WebsetsBaseClient
from ..core.async_base import WebsetsAsyncBaseClient
from .runs import MonitorRunsClient

class MonitorsClient(WebsetsBaseClient):
    """Client for managing Monitors."""
    
    def __init__(self, client):
        super().__init__(client)
        self.runs = MonitorRunsClient(client)

    def create(self, params: Union[Dict[str, Any], CreateMonitorParameters]) -> Monitor:
        """Create a new Monitor to continuously keep your Websets updated with fresh data.
        
        Monitors automatically run on your defined schedule to ensure your Websets stay current without manual intervention:
        - Find new content: Execute search operations to discover fresh items matching your criteria
        - Update existing content: Run refresh operations to update items contents and enrichments
        - Automated scheduling: Configure frequency, timezone, and execution times
        
        Args:
            params (CreateMonitorParameters): The parameters for creating a monitor.
        
        Returns:
            Monitor: The created monitor.
        """
        response = self.request("/v0/monitors", data=params)
        return Monitor.model_validate(response)

    def get(self, monitor_id: str) -> Monitor:
        """Get a specific monitor.
        
        Args:
            monitor_id (str): The id of the Monitor.
        
        Returns:
            Monitor: The retrieved monitor.
        """
        response = self.request(f"/v0/monitors/{monitor_id}", method="GET")
        return Monitor.model_validate(response)

    def list(self, *, cursor: Optional[str] = None, limit: Optional[int] = None, webset_id: Optional[str] = None) -> ListMonitorsResponse:
        """List all monitors.
        
        Args:
            cursor (str, optional): The cursor to paginate through the results.
            limit (int, optional): The number of results to return (1-200, default 25).
            webset_id (str, optional): The id of the Webset to list monitors for.
        
        Returns:
            ListMonitorsResponse: List of monitors with pagination info.
        """
        params = {
            k: v 
            for k, v in {
                "cursor": cursor, 
                "limit": limit, 
                "websetId": webset_id
            }.items() 
            if v is not None
        }
        response = self.request("/v0/monitors", params=params, method="GET")
        return ListMonitorsResponse.model_validate(response)

    def update(self, monitor_id: str, params: Union[Dict[str, Any], UpdateMonitor]) -> Monitor:
        """Update a monitor configuration.
        
        Args:
            monitor_id (str): The id of the Monitor.
            params (UpdateMonitor): The parameters for updating a monitor.
        
        Returns:
            Monitor: The updated monitor.
        """
        response = self.request(f"/v0/monitors/{monitor_id}", data=params, method="PATCH")
        return Monitor.model_validate(response)

    def delete(self, monitor_id: str) -> Monitor:
        """Delete a monitor.
        
        Args:
            monitor_id (str): The id of the Monitor.
        
        Returns:
            Monitor: The deleted monitor.
        """
        response = self.request(f"/v0/monitors/{monitor_id}", method="DELETE")
        return Monitor.model_validate(response)


class AsyncMonitorsClient(WebsetsAsyncBaseClient):
    """Async client for managing Monitors."""
    
    def __init__(self, client):
        super().__init__(client)
        from .runs import AsyncMonitorRunsClient
        self.runs = AsyncMonitorRunsClient(client)

    async def create(self, params: Union[Dict[str, Any], CreateMonitorParameters]) -> Monitor:
        """Create a new Monitor to continuously keep your Websets updated with fresh data."""
        response = await self.request("/v0/monitors", data=params)
        return Monitor.model_validate(response)

    async def get(self, monitor_id: str) -> Monitor:
        """Get a specific monitor."""
        response = await self.request(f"/v0/monitors/{monitor_id}", method="GET")
        return Monitor.model_validate(response)

    async def list(self, *, cursor: Optional[str] = None, limit: Optional[int] = None, webset_id: Optional[str] = None) -> ListMonitorsResponse:
        """List all monitors."""
        params = {k: v for k, v in {"cursor": cursor, "limit": limit, "websetId": webset_id}.items() if v is not None}
        response = await self.request("/v0/monitors", params=params, method="GET")
        return ListMonitorsResponse.model_validate(response)

    async def update(self, monitor_id: str, params: Union[Dict[str, Any], UpdateMonitor]) -> Monitor:
        """Update a monitor configuration."""
        response = await self.request(f"/v0/monitors/{monitor_id}", data=params, method="PATCH")
        return Monitor.model_validate(response)

    async def delete(self, monitor_id: str) -> Monitor:
        """Delete a monitor."""
        response = await self.request(f"/v0/monitors/{monitor_id}", method="DELETE")
        return Monitor.model_validate(response) 