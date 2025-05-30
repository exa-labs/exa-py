from __future__ import annotations

from ...types import (
    StreamRun,
    ListStreamRunsResponse,
)
from ...core.base import WebsetsBaseClient

class StreamRunsClient(WebsetsBaseClient):
    """Client for managing Stream Runs."""
    
    def __init__(self, client):
        super().__init__(client)

    def list(self, stream_id: str) -> ListStreamRunsResponse:
        """List all runs for the Stream.
        
        Args:
            stream_id (str): The id of the Stream to list runs for.
        
        Returns:
            ListStreamRunsResponse: List of stream runs.
        """
        response = self.request(f"/v0/streams/{stream_id}/runs", method="GET")
        return ListStreamRunsResponse.model_validate(response)

    def get(self, stream_id: str, run_id: str) -> StreamRun:
        """Get a specific stream run.
        
        Args:
            stream_id (str): The id of the Stream to get the run for.
            run_id (str): The id of the stream run.
        
        Returns:
            StreamRun: The stream run details.
        """
        response = self.request(f"/v0/streams/{stream_id}/runs/{run_id}", method="GET")
        return StreamRun.model_validate(response) 