from __future__ import annotations

from typing import Dict, Any, Union, Optional

from ..types import (
    Stream,
    CreateStreamParameters,
    UpdateStream,
    ListStreamsResponse,
)
from ..core.base import WebsetsBaseClient
from .runs import StreamRunsClient

class StreamsClient(WebsetsBaseClient):
    """Client for managing Streams."""
    
    def __init__(self, client):
        super().__init__(client)
        self.runs = StreamRunsClient(client)

    def create(self, params: Union[Dict[str, Any], CreateStreamParameters]) -> Stream:
        """Create a new Stream to continuously keep your Websets updated with fresh data.
        
        Streams automatically run on your defined schedule to ensure your Websets stay current without manual intervention:
        - Find new content: Execute search operations to discover fresh items matching your criteria
        - Update existing content: Run refresh operations to update items contents and enrichments
        - Automated scheduling: Configure frequency, timezone, and execution times
        
        Args:
            params (CreateStreamParameters): The parameters for creating a stream.
        
        Returns:
            Stream: The created stream.
        """
        response = self.request("/v0/streams", data=params)
        return Stream.model_validate(response)

    def get(self, stream_id: str) -> Stream:
        """Get a specific stream.
        
        Args:
            stream_id (str): The id of the Stream.
        
        Returns:
            Stream: The retrieved stream.
        """
        response = self.request(f"/v0/streams/{stream_id}", method="GET")
        return Stream.model_validate(response)

    def list(self, *, cursor: Optional[str] = None, limit: Optional[int] = None, webset_id: Optional[str] = None) -> ListStreamsResponse:
        """List all streams.
        
        Args:
            cursor (str, optional): The cursor to paginate through the results.
            limit (int, optional): The number of results to return (1-200, default 25).
            webset_id (str, optional): The id of the Webset to list streams for.
        
        Returns:
            ListStreamsResponse: List of streams with pagination info.
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
        response = self.request("/v0/streams", params=params, method="GET")
        return ListStreamsResponse.model_validate(response)

    def update(self, stream_id: str, params: Union[Dict[str, Any], UpdateStream]) -> Stream:
        """Update a stream configuration.
        
        Args:
            stream_id (str): The id of the Stream.
            params (UpdateStream): The parameters for updating a stream.
        
        Returns:
            Stream: The updated stream.
        """
        response = self.request(f"/v0/streams/{stream_id}", data=params, method="PATCH")
        return Stream.model_validate(response)

    def delete(self, stream_id: str) -> Stream:
        """Delete a stream.
        
        Args:
            stream_id (str): The id of the Stream.
        
        Returns:
            Stream: The deleted stream.
        """
        response = self.request(f"/v0/streams/{stream_id}", method="DELETE")
        return Stream.model_validate(response) 