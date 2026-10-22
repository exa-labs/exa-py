from __future__ import annotations

from typing import List, Optional
from typing_extensions import Unpack

from pydantic import TypeAdapter

from ..types import (
    Event,
    EventType,
    ListEventsResponse,
)

# Re-exported: code written against earlier releases imports the event classes from this module.
from ..types import (  # noqa: F401
    ImportCompletedEvent,
    ImportCreatedEvent,
    MonitorCreatedEvent,
    MonitorDeletedEvent,
    MonitorRunCompletedEvent,
    MonitorRunCreatedEvent,
    MonitorUpdatedEvent,
    WebsetCreatedEvent,
    WebsetDeletedEvent,
    WebsetIdleEvent,
    WebsetItemCreatedEvent,
    WebsetItemEnrichedEvent,
    WebsetPausedEvent,
    WebsetSearchCanceledEvent,
    WebsetSearchCompletedEvent,
    WebsetSearchCreatedEvent,
    WebsetSearchUpdatedEvent,
)
from ..core.base import WebsetsBaseClient
from ..core.async_base import WebsetsAsyncBaseClient
from ...request_options import ExtraRequestOptions

_EVENT_ADAPTER: TypeAdapter[Event] = TypeAdapter(Event)
"""Validates one event. A type this SDK version does not list parses as ``UnknownEvent``."""

class EventsClient(WebsetsBaseClient):
    """Client for managing Events."""
    
    def __init__(self, client):
        super().__init__(client)

    def list(self, *, cursor: Optional[str] = None, limit: Optional[int] = None, 
             types: Optional[List[EventType]] = None, **extra: Unpack[ExtraRequestOptions]) -> ListEventsResponse:
        """List all Events.
        
        Args:
            cursor (str, optional): The cursor to paginate through the results.
            limit (int, optional): The number of results to return.
            types (List[EventType], optional): The types of events to filter by.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).
        
        Returns:
            ListEventsResponse: List of events.
        """
        params = {}
        if cursor is not None:
            params["cursor"] = cursor
        if limit is not None:
            params["limit"] = limit
        if types is not None:
            # Convert EventType enums to their string values
            params["types"] = [t.value if hasattr(t, 'value') else t for t in types]
            
        response = self.request("/v0/events", params=params, method="GET", **extra)
        return ListEventsResponse.model_validate(response)

    def get(self, id: str, **extra: Unpack[ExtraRequestOptions]) -> Event:
        """Get an Event by ID.
        
        Args:
            id (str): The ID of the Event.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).
        
        Returns:
            Event: The retrieved event.
        """
        response = self.request(f"/v0/events/{id}", method="GET", **extra)
        return _EVENT_ADAPTER.validate_python(response)


class AsyncEventsClient(WebsetsAsyncBaseClient):
    """Async client for managing Events."""
    
    def __init__(self, client):
        super().__init__(client)

    async def list(self, *, cursor: Optional[str] = None, limit: Optional[int] = None, 
             types: Optional[List[EventType]] = None, **extra: Unpack[ExtraRequestOptions]) -> ListEventsResponse:
        """List all Events.
        
        Args:
            cursor (str, optional): The cursor to paginate through the results.
            limit (int, optional): The number of results to return.
            types (List[EventType], optional): The types of events to filter by.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).
        
        Returns:
            ListEventsResponse: List of events.
        """
        params = {}
        if cursor is not None:
            params["cursor"] = cursor
        if limit is not None:
            params["limit"] = limit
        if types is not None:
            # Convert EventType enums to their string values
            params["types"] = [t.value if hasattr(t, 'value') else t for t in types]
            
        response = await self.request("/v0/events", params=params, method="GET", **extra)
        return ListEventsResponse.model_validate(response)

    async def get(self, id: str, **extra: Unpack[ExtraRequestOptions]) -> Event:
        """Get an Event by ID.
        
        Args:
            id (str): The ID of the Event.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).
        
        Returns:
            Event: The retrieved event.
        """
        response = await self.request(f"/v0/events/{id}", method="GET", **extra)
        return _EVENT_ADAPTER.validate_python(response)
