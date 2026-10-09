"""Asynchronous Search Monitors API client."""

from __future__ import annotations

from typing import Any, AsyncIterator, Dict, List, Optional, Union
from typing_extensions import Unpack

from .async_base import SearchMonitorsAsyncBaseClient
from .types import (
    CreateSearchMonitorParams,
    CreateSearchMonitorResponse,
    ListSearchMonitorRunsResponse,
    ListSearchMonitorsResponse,
    SearchMonitor,
    SearchMonitorRun,
    SearchMonitorStatus,
    TriggerSearchMonitorResponse,
    UpdateSearchMonitorParams,
)
from ..request_options import ExtraRequestOptions, options_for_next_page


class AsyncSearchMonitorRunsClient(SearchMonitorsAsyncBaseClient):
    """Asynchronous client for managing Search Monitor Runs."""

    async def list(
        self,
        monitor_id: str,
        *,
        cursor: Optional[str] = None,
        limit: Optional[int] = None,
        **extra: Unpack[ExtraRequestOptions],
    ) -> ListSearchMonitorRunsResponse:
        """List all runs for a Search Monitor.

        Args:
            monitor_id: The ID of the Search Monitor.
            cursor: Pagination cursor from a previous response.
            limit: Maximum number of results to return.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).

        Returns:
            List of Search Monitor runs with pagination info.
        """
        params = self.build_pagination_params(cursor, limit)
        response = await self.request(
            f"/{monitor_id}/runs", method="GET", params=params,
            **extra,
        )
        return ListSearchMonitorRunsResponse.model_validate(response)

    async def get(self, monitor_id: str, run_id: str, **extra: Unpack[ExtraRequestOptions]) -> SearchMonitorRun:
        """Get a specific Search Monitor run.

        Args:
            monitor_id: The ID of the Search Monitor.
            run_id: The ID of the run.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).

        Returns:
            The Search Monitor run.
        """
        response = await self.request(
            f"/{monitor_id}/runs/{run_id}", method="GET",
            **extra,
        )
        return SearchMonitorRun.model_validate(response)

    async def list_all(self, monitor_id: str, *, limit: Optional[int] = None, **extra: Unpack[ExtraRequestOptions]) -> AsyncIterator[SearchMonitorRun]:
        """Iterate through all runs for a Search Monitor, handling pagination automatically.

        Args:
            monitor_id: The ID of the Search Monitor.
            limit: Maximum number of results to return per page.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).

        Yields:
            SearchMonitorRun: Each run.
        """
        cursor = None
        while True:
            response = await self.list(monitor_id, cursor=cursor, limit=limit, **extra)
            for run in response.data:
                yield run
            if not response.has_more or not response.next_cursor:
                break
            cursor = response.next_cursor
            extra = options_for_next_page(extra)

    async def get_all(self, monitor_id: str, *, limit: Optional[int] = None, **extra: Unpack[ExtraRequestOptions]) -> List[SearchMonitorRun]:
        """Collect all runs for a Search Monitor into a list.

        Args:
            monitor_id: The ID of the Search Monitor.
            limit: Maximum number of results to return per page.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).

        Returns:
            List of all Search Monitor runs.
        """
        items = []
        async for run in self.list_all(monitor_id, limit=limit, **extra):
            items.append(run)
        return items


class AsyncSearchMonitorsClient(SearchMonitorsAsyncBaseClient):
    """Asynchronous client for managing Search Monitors."""

    runs: AsyncSearchMonitorRunsClient

    def __init__(self, client: Any):
        super().__init__(client)
        self.runs = AsyncSearchMonitorRunsClient(client)

    async def create(
        self, params: Union[Dict[str, Any], CreateSearchMonitorParams],
        **extra: Unpack[ExtraRequestOptions],
    ) -> CreateSearchMonitorResponse:
        """Create a Search Monitor.

        Args:
            params: The monitor creation parameters.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).

        Returns:
            The created Search Monitor with webhookSecret.
        """
        data = params if isinstance(params, dict) else params.model_dump(by_alias=True, exclude_none=True)
        response = await self.request("", method="POST", data=data, **extra)
        return CreateSearchMonitorResponse.model_validate(response)

    async def get(self, monitor_id: str, **extra: Unpack[ExtraRequestOptions]) -> SearchMonitor:
        """Get a Search Monitor by ID.

        Args:
            monitor_id: The ID of the Search Monitor.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).

        Returns:
            The Search Monitor.
        """
        response = await self.request(f"/{monitor_id}", method="GET", **extra)
        return SearchMonitor.model_validate(response)

    async def list(
        self,
        *,
        status: Optional[SearchMonitorStatus] = None,
        cursor: Optional[str] = None,
        limit: Optional[int] = None,
        **extra: Unpack[ExtraRequestOptions],
    ) -> ListSearchMonitorsResponse:
        """List Search Monitors.

        Args:
            status: Filter by monitor status.
            cursor: Pagination cursor from a previous response.
            limit: Maximum number of results to return.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).

        Returns:
            List of Search Monitors with pagination info.
        """
        params = self.build_pagination_params(cursor, limit)
        if status is not None:
            params["status"] = status
        response = await self.request("", method="GET", params=params, **extra)
        return ListSearchMonitorsResponse.model_validate(response)

    async def update(
        self, monitor_id: str, params: Union[Dict[str, Any], UpdateSearchMonitorParams],
        **extra: Unpack[ExtraRequestOptions],
    ) -> SearchMonitor:
        """Update a Search Monitor.

        Args:
            monitor_id: The ID of the Search Monitor.
            params: The update parameters.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).

        Returns:
            The updated Search Monitor.
        """
        data = params if isinstance(params, dict) else params.model_dump(by_alias=True, exclude_none=True)
        response = await self.request(
            f"/{monitor_id}", method="PATCH", data=data,
            **extra,
        )
        return SearchMonitor.model_validate(response)

    async def delete(self, monitor_id: str, **extra: Unpack[ExtraRequestOptions]) -> SearchMonitor:
        """Delete a Search Monitor.

        Args:
            monitor_id: The ID of the Search Monitor.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).

        Returns:
            The deleted Search Monitor.
        """
        response = await self.request(f"/{monitor_id}", method="DELETE", **extra)
        return SearchMonitor.model_validate(response)

    async def list_all(self, *, status: Optional[SearchMonitorStatus] = None, limit: Optional[int] = None, **extra: Unpack[ExtraRequestOptions]) -> AsyncIterator[SearchMonitor]:
        """Iterate through all Search Monitors, handling pagination automatically.

        Args:
            status: Filter by monitor status.
            limit: Maximum number of results to return per page.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).

        Yields:
            SearchMonitor: Each monitor.
        """
        cursor = None
        while True:
            response = await self.list(status=status, cursor=cursor, limit=limit, **extra)
            for monitor in response.data:
                yield monitor
            if not response.has_more or not response.next_cursor:
                break
            cursor = response.next_cursor
            extra = options_for_next_page(extra)

    async def get_all(self, *, status: Optional[SearchMonitorStatus] = None, limit: Optional[int] = None, **extra: Unpack[ExtraRequestOptions]) -> List[SearchMonitor]:
        """Collect all Search Monitors into a list.

        Args:
            status: Filter by monitor status.
            limit: Maximum number of results to return per page.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).

        Returns:
            List of all Search Monitors.
        """
        items = []
        async for monitor in self.list_all(status=status, limit=limit, **extra):
            items.append(monitor)
        return items

    async def trigger(self, monitor_id: str, **extra: Unpack[ExtraRequestOptions]) -> TriggerSearchMonitorResponse:
        """Trigger a Search Monitor run immediately.

        Args:
            monitor_id: The ID of the Search Monitor.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).

        Returns:
            TriggerSearchMonitorResponse with 'triggered' boolean.
        """
        response = await self.request(
            f"/{monitor_id}/trigger", method="POST",
            **extra,
        )
        return TriggerSearchMonitorResponse.model_validate(response)
