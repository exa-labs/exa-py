"""Synchronous Search Monitors API client."""

from __future__ import annotations

from typing import Any, Dict, Iterator, List, Optional, Union

from .base import SearchMonitorsBaseClient
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


class SearchMonitorRunsClient(SearchMonitorsBaseClient):
    """Synchronous client for managing Search Monitor Runs."""

    def list(
        self,
        monitor_id: str,
        *,
        cursor: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> ListSearchMonitorRunsResponse:
        """List all runs for a Search Monitor.

        Args:
            monitor_id: The ID of the Search Monitor.
            cursor: Pagination cursor from a previous response.
            limit: Maximum number of results to return.

        Returns:
            List of Search Monitor runs with pagination info.

        Examples:
            from exa_py import Exa
            import os

            exa = Exa(os.environ["EXA_API_KEY"])

            runs = exa.monitors.runs.list("sm_123", limit=10)
            print(runs.data[0].status if runs.data else "no runs yet")
        """
        params = self.build_pagination_params(cursor, limit)
        response = self.request(
            f"/{monitor_id}/runs", method="GET", params=params
        )
        return ListSearchMonitorRunsResponse.model_validate(response)

    def get(self, monitor_id: str, run_id: str) -> SearchMonitorRun:
        """Get a specific Search Monitor run.

        Args:
            monitor_id: The ID of the Search Monitor.
            run_id: The ID of the run.

        Returns:
            The Search Monitor run.

        Examples:
            from exa_py import Exa
            import os

            exa = Exa(os.environ["EXA_API_KEY"])

            run = exa.monitors.runs.get("sm_123", "run_456")
            print(run.status)
        """
        response = self.request(
            f"/{monitor_id}/runs/{run_id}", method="GET"
        )
        return SearchMonitorRun.model_validate(response)

    def list_all(self, monitor_id: str, *, limit: Optional[int] = None) -> Iterator[SearchMonitorRun]:
        """Iterate through all runs for a Search Monitor, handling pagination automatically.

        Args:
            monitor_id: The ID of the Search Monitor.
            limit: Maximum number of results to return per page.

        Yields:
            SearchMonitorRun: Each run.
        """
        cursor = None
        while True:
            response = self.list(monitor_id, cursor=cursor, limit=limit)
            for run in response.data:
                yield run
            if not response.has_more or not response.next_cursor:
                break
            cursor = response.next_cursor

    def get_all(self, monitor_id: str, *, limit: Optional[int] = None) -> List[SearchMonitorRun]:
        """Collect all runs for a Search Monitor into a list.

        Args:
            monitor_id: The ID of the Search Monitor.
            limit: Maximum number of results to return per page.

        Returns:
            List of all Search Monitor runs.
        """
        return list(self.list_all(monitor_id, limit=limit))


class SearchMonitorsClient(SearchMonitorsBaseClient):
    """Synchronous client for managing Search Monitors."""

    runs: SearchMonitorRunsClient

    def __init__(self, client: Any):
        super().__init__(client)
        self.runs = SearchMonitorRunsClient(client)

    def create(
        self, params: Union[Dict[str, Any], CreateSearchMonitorParams]
    ) -> CreateSearchMonitorResponse:
        """Create a Search Monitor.

        Args:
            params: The monitor creation parameters.

        Returns:
            The created Search Monitor with webhookSecret.

        Examples:
            from exa_py import Exa
            import os

            exa = Exa(os.environ["EXA_API_KEY"])

            monitor = exa.monitors.create(
                {
                    "name": "AI startup funding monitor",
                    "search": {
                        "query": "site:techcrunch.com AI startup funding round",
                        "numResults": 5,
                    },
                    "trigger": {
                        "type": "cron",
                        "expression": "0 * * * *",
                        "timezone": "UTC",
                    },
                    "webhook": {
                        "url": "https://example.com/webhooks/search-monitors",
                        "events": ["monitor.run.completed"],
                    },
                }
            )

            print(monitor.id)
        """
        data = params if isinstance(params, dict) else params.model_dump(by_alias=True, exclude_none=True)
        response = self.request("", method="POST", data=data)
        return CreateSearchMonitorResponse.model_validate(response)

    def get(self, monitor_id: str) -> SearchMonitor:
        """Get a Search Monitor by ID.

        Args:
            monitor_id: The ID of the Search Monitor.

        Returns:
            The Search Monitor.

        Examples:
            from exa_py import Exa
            import os

            exa = Exa(os.environ["EXA_API_KEY"])

            monitor = exa.monitors.get("sm_123")
            print(monitor.status)
        """
        response = self.request(f"/{monitor_id}", method="GET")
        return SearchMonitor.model_validate(response)

    def list(
        self,
        *,
        status: Optional[SearchMonitorStatus] = None,
        cursor: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> ListSearchMonitorsResponse:
        """List Search Monitors.

        Args:
            status: Filter by monitor status.
            cursor: Pagination cursor from a previous response.
            limit: Maximum number of results to return.

        Returns:
            List of Search Monitors with pagination info.

        Examples:
            from exa_py import Exa
            import os

            exa = Exa(os.environ["EXA_API_KEY"])

            monitors = exa.monitors.list(status="active", limit=20)
            print([monitor.name for monitor in monitors.data])
        """
        params = self.build_pagination_params(cursor, limit)
        if status is not None:
            params["status"] = status
        response = self.request("", method="GET", params=params)
        return ListSearchMonitorsResponse.model_validate(response)

    def update(
        self, monitor_id: str, params: Union[Dict[str, Any], UpdateSearchMonitorParams]
    ) -> SearchMonitor:
        """Update a Search Monitor.

        Args:
            monitor_id: The ID of the Search Monitor.
            params: The update parameters.

        Returns:
            The updated Search Monitor.

        Examples:
            from exa_py import Exa
            import os

            exa = Exa(os.environ["EXA_API_KEY"])

            monitor = exa.monitors.update(
                "sm_123",
                {
                    "status": "paused",
                    "name": "Paused funding monitor",
                },
            )

            print(monitor.updated_at)
        """
        data = params if isinstance(params, dict) else params.model_dump(by_alias=True, exclude_none=True)
        response = self.request(f"/{monitor_id}", method="PATCH", data=data)
        return SearchMonitor.model_validate(response)

    def delete(self, monitor_id: str) -> SearchMonitor:
        """Delete a Search Monitor.

        Args:
            monitor_id: The ID of the Search Monitor.

        Returns:
            The deleted Search Monitor.

        Examples:
            from exa_py import Exa
            import os

            exa = Exa(os.environ["EXA_API_KEY"])

            deleted_monitor = exa.monitors.delete("sm_123")
            print(deleted_monitor.status)
        """
        response = self.request(f"/{monitor_id}", method="DELETE")
        return SearchMonitor.model_validate(response)

    def list_all(self, *, status: Optional[SearchMonitorStatus] = None, limit: Optional[int] = None) -> Iterator[SearchMonitor]:
        """Iterate through all Search Monitors, handling pagination automatically.

        Args:
            status: Filter by monitor status.
            limit: Maximum number of results to return per page.

        Yields:
            SearchMonitor: Each monitor.
        """
        cursor = None
        while True:
            response = self.list(status=status, cursor=cursor, limit=limit)
            for monitor in response.data:
                yield monitor
            if not response.has_more or not response.next_cursor:
                break
            cursor = response.next_cursor

    def get_all(self, *, status: Optional[SearchMonitorStatus] = None, limit: Optional[int] = None) -> List[SearchMonitor]:
        """Collect all Search Monitors into a list.

        Args:
            status: Filter by monitor status.
            limit: Maximum number of results to return per page.

        Returns:
            List of all Search Monitors.
        """
        return list(self.list_all(status=status, limit=limit))

    def trigger(self, monitor_id: str) -> TriggerSearchMonitorResponse:
        """Trigger a Search Monitor run immediately.

        Args:
            monitor_id: The ID of the Search Monitor.

        Returns:
            TriggerSearchMonitorResponse with 'triggered' boolean.

        Examples:
            from exa_py import Exa
            import os

            exa = Exa(os.environ["EXA_API_KEY"])

            response = exa.monitors.trigger("sm_123")
            print(response.triggered)
        """
        response = self.request(f"/{monitor_id}/trigger", method="POST")
        return TriggerSearchMonitorResponse.model_validate(response)
