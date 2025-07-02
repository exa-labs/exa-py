from __future__ import annotations

from ...types import (
    MonitorRun,
    ListMonitorRunsResponse,
)
from ...core.base import WebsetsBaseClient

class MonitorRunsClient(WebsetsBaseClient):
    """Client for managing Monitor Runs."""
    
    def __init__(self, client: Any) -> None:
        super().__init__(client)

    def list(self, monitor_id: str) -> ListMonitorRunsResponse:
        """List all runs for the Monitor.
        
        Args:
            monitor_id (str): The id of the Monitor to list runs for.
        
        Returns:
            ListMonitorRunsResponse: List of monitor runs.
        """
        response = self.request(f"/v0/monitors/{monitor_id}/runs", method="GET")
        return ListMonitorRunsResponse.model_validate(response)

    def get(self, monitor_id: str, run_id: str) -> MonitorRun:
        """Get a specific monitor run.
        
        Args:
            monitor_id (str): The id of the Monitor to get the run for.
            run_id (str): The id of the monitor run.
        
        Returns:
            MonitorRun: The monitor run details.
        """
        response = self.request(f"/v0/monitors/{monitor_id}/runs/{run_id}", method="GET")
        return MonitorRun.model_validate(response) 