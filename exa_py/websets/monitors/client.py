from __future__ import annotations

from typing import Any, AsyncIterator, Dict, Iterator, List, Optional, Union
from typing_extensions import Unpack

from ..types import (
    Monitor,
    CreateMonitorParameters,
    UpdateMonitor,
    ListMonitorsResponse,
)
from ..core.base import WebsetsBaseClient
from ..core.async_base import WebsetsAsyncBaseClient
from .runs import MonitorRunsClient
from ...request_options import ExtraRequestOptions, options_for_next_page

class MonitorsClient(WebsetsBaseClient):
    """Client for managing Monitors."""
    
    def __init__(self, client):
        super().__init__(client)
        self.runs = MonitorRunsClient(client)

    def create(self, params: Union[Dict[str, Any], CreateMonitorParameters], **extra: Unpack[ExtraRequestOptions]) -> Monitor:
        """Create a Monitor that searches for new Items for a Webset.

        The Monitor runs on the `cron` schedule in the given `timezone`.
        
        Args:
            params (CreateMonitorParameters): The parameters for creating a monitor.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).
        
        Returns:
            Monitor: The created monitor.
        """
        response = self.request("/v0/monitors", data=params, **extra)
        return Monitor.model_validate(response)

    def get(self, monitor_id: str, **extra: Unpack[ExtraRequestOptions]) -> Monitor:
        """Get a specific monitor.
        
        Args:
            monitor_id (str): The id of the Monitor.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).
        
        Returns:
            Monitor: The retrieved monitor.
        """
        response = self.request(f"/v0/monitors/{monitor_id}", method="GET", **extra)
        return Monitor.model_validate(response)

    def list(self, *, cursor: Optional[str] = None, limit: Optional[int] = None, webset_id: Optional[str] = None, **extra: Unpack[ExtraRequestOptions]) -> ListMonitorsResponse:
        """List all monitors.
        
        Args:
            cursor (str, optional): The cursor to paginate through the results.
            limit (int, optional): The number of results to return (1-200, default 25).
            webset_id (str, optional): The id of the Webset to list monitors for.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).
        
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
        response = self.request("/v0/monitors", params=params, method="GET", **extra)
        return ListMonitorsResponse.model_validate(response)

    def update(self, monitor_id: str, params: Union[Dict[str, Any], UpdateMonitor], **extra: Unpack[ExtraRequestOptions]) -> Monitor:
        """Update a monitor configuration.
        
        Args:
            monitor_id (str): The id of the Monitor.
            params (UpdateMonitor): The parameters for updating a monitor.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).
        
        Returns:
            Monitor: The updated monitor.
        """
        response = self.request(f"/v0/monitors/{monitor_id}", data=params, method="PATCH", **extra)
        return Monitor.model_validate(response)

    def delete(self, monitor_id: str, **extra: Unpack[ExtraRequestOptions]) -> Monitor:
        """Delete a monitor.
        
        Args:
            monitor_id (str): The id of the Monitor.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).
        
        Returns:
            Monitor: The deleted monitor.
        """
        response = self.request(f"/v0/monitors/{monitor_id}", method="DELETE", **extra)
        return Monitor.model_validate(response)

    def list_all(self, *, limit: Optional[int] = None, webset_id: Optional[str] = None, **extra: Unpack[ExtraRequestOptions]) -> Iterator[Monitor]:
        """Iterate through all Monitors, handling pagination automatically.

        Args:
            limit (int, optional): The number of results to return per page (1-200, default 25).
            webset_id (str, optional): The id of the Webset to list monitors for.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).

        Yields:
            Monitor: Each monitor.

        Examples:
            from exa_py import Exa
            import os

            exa = Exa(os.environ["EXA_API_KEY"])
            for monitor in exa.websets.monitors.list_all(webset_id="ws_123"):
                print(monitor.id)
        """
        cursor = None
        while True:
            response = self.list(cursor=cursor, limit=limit, webset_id=webset_id, **extra)
            for monitor in response.data:
                yield monitor

            if not response.has_more or not response.next_cursor:
                break

            cursor = response.next_cursor
            extra = options_for_next_page(extra)

    def get_all(self, *, limit: Optional[int] = None, webset_id: Optional[str] = None, **extra: Unpack[ExtraRequestOptions]) -> List[Monitor]:
        """Collect all Monitors into a list.

        Args:
            limit (int, optional): The number of results to return per page (1-200, default 25).
            webset_id (str, optional): The id of the Webset to list monitors for.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).

        Returns:
            List[Monitor]: All monitors.

        Examples:
            from exa_py import Exa
            import os

            exa = Exa(os.environ["EXA_API_KEY"])
            monitors = exa.websets.monitors.get_all(webset_id="ws_123")
        """
        return list(self.list_all(limit=limit, webset_id=webset_id, **extra))


class AsyncMonitorsClient(WebsetsAsyncBaseClient):
    """Async client for managing Monitors."""
    
    def __init__(self, client):
        super().__init__(client)
        from .runs import AsyncMonitorRunsClient
        self.runs = AsyncMonitorRunsClient(client)

    async def create(self, params: Union[Dict[str, Any], CreateMonitorParameters], **extra: Unpack[ExtraRequestOptions]) -> Monitor:
        """Create a Monitor that searches for new Items for a Webset.

        The Monitor runs on the `cron` schedule in the given `timezone`.

        Args:
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).
        """
        response = await self.request("/v0/monitors", data=params, **extra)
        return Monitor.model_validate(response)

    async def get(self, monitor_id: str, **extra: Unpack[ExtraRequestOptions]) -> Monitor:
        """Get a specific monitor.

        Args:
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).
        """
        response = await self.request(f"/v0/monitors/{monitor_id}", method="GET", **extra)
        return Monitor.model_validate(response)

    async def list(self, *, cursor: Optional[str] = None, limit: Optional[int] = None, webset_id: Optional[str] = None, **extra: Unpack[ExtraRequestOptions]) -> ListMonitorsResponse:
        """List all monitors.

        Args:
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).
        """
        params = {k: v for k, v in {"cursor": cursor, "limit": limit, "websetId": webset_id}.items() if v is not None}
        response = await self.request("/v0/monitors", params=params, method="GET", **extra)
        return ListMonitorsResponse.model_validate(response)

    async def update(self, monitor_id: str, params: Union[Dict[str, Any], UpdateMonitor], **extra: Unpack[ExtraRequestOptions]) -> Monitor:
        """Update a monitor configuration.

        Args:
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).
        """
        response = await self.request(f"/v0/monitors/{monitor_id}", data=params, method="PATCH", **extra)
        return Monitor.model_validate(response)

    async def delete(self, monitor_id: str, **extra: Unpack[ExtraRequestOptions]) -> Monitor:
        """Delete a monitor.

        Args:
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).
        """
        response = await self.request(f"/v0/monitors/{monitor_id}", method="DELETE", **extra)
        return Monitor.model_validate(response)

    async def list_all(self, *, limit: Optional[int] = None, webset_id: Optional[str] = None, **extra: Unpack[ExtraRequestOptions]) -> AsyncIterator[Monitor]:
        """Iterate through all Monitors, handling pagination automatically.

        Args:
            limit (int, optional): The number of results to return per page (1-200, default 25).
            webset_id (str, optional): The id of the Webset to list monitors for.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).

        Yields:
            Monitor: Each monitor.

        Examples:
            from exa_py import AsyncExa
            import os

            exa = AsyncExa(os.environ["EXA_API_KEY"])
            async for monitor in exa.websets.monitors.list_all(webset_id="ws_123"):
                print(monitor.id)
        """
        cursor = None
        while True:
            response = await self.list(cursor=cursor, limit=limit, webset_id=webset_id, **extra)
            for monitor in response.data:
                yield monitor

            if not response.has_more or not response.next_cursor:
                break

            cursor = response.next_cursor
            extra = options_for_next_page(extra)

    async def get_all(self, *, limit: Optional[int] = None, webset_id: Optional[str] = None, **extra: Unpack[ExtraRequestOptions]) -> List[Monitor]:
        """Collect all Monitors into a list.

        Args:
            limit (int, optional): The number of results to return per page (1-200, default 25).
            webset_id (str, optional): The id of the Webset to list monitors for.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).

        Returns:
            List[Monitor]: All monitors.

        Examples:
            from exa_py import AsyncExa
            import os

            exa = AsyncExa(os.environ["EXA_API_KEY"])
            monitors = await exa.websets.monitors.get_all(webset_id="ws_123")
        """
        monitors = []
        async for monitor in self.list_all(limit=limit, webset_id=webset_id, **extra):
            monitors.append(monitor)
        return monitors
