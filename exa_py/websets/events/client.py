from __future__ import annotations

from typing import List, Optional, Union, Iterator, AsyncIterator

from ..types import (
    EventType,
    ListEventsResponse,
    WebsetCreatedEvent,
    WebsetDeletedEvent,
    WebsetIdleEvent,
    WebsetPausedEvent,
    WebsetItemCreatedEvent,
    WebsetItemEnrichedEvent,
    WebsetSearchCreatedEvent,
    WebsetSearchUpdatedEvent,
    WebsetSearchCanceledEvent,
    WebsetSearchCompletedEvent,
    ImportCreatedEvent,
    ImportCompletedEvent,
    MonitorCreatedEvent,
    MonitorUpdatedEvent,
    MonitorDeletedEvent,
    MonitorRunCreatedEvent,
    MonitorRunCompletedEvent,
)
from ..core.base import WebsetsBaseClient
from ..core.async_base import WebsetsAsyncBaseClient

# Type alias for all event types
Event = Union[
    WebsetCreatedEvent,
    WebsetDeletedEvent,
    WebsetIdleEvent,
    WebsetPausedEvent,
    WebsetItemCreatedEvent,
    WebsetItemEnrichedEvent,
    WebsetSearchCreatedEvent,
    WebsetSearchUpdatedEvent,
    WebsetSearchCanceledEvent,
    WebsetSearchCompletedEvent,
    ImportCreatedEvent,
    ImportCompletedEvent,
    MonitorCreatedEvent,
    MonitorUpdatedEvent,
    MonitorDeletedEvent,
    MonitorRunCreatedEvent,
    MonitorRunCompletedEvent,
]

class EventsClient(WebsetsBaseClient):
    """Client for managing Events."""
    
    def __init__(self, client):
        super().__init__(client)

    def list(self, *, cursor: Optional[str] = None, limit: Optional[int] = None, 
             types: Optional[List[EventType]] = None) -> ListEventsResponse:
        """List all Events."""
        params = {}
        if cursor is not None:
            params["cursor"] = cursor
        if limit is not None:
            params["limit"] = limit
        if types is not None:
            params["types"] = [t.value if hasattr(t, 'value') else t for t in types]
            
        response = self.request("/v0/events", params=params, method="GET")
        return ListEventsResponse.model_validate(response)

    def get(self, id: str) -> Event:
        """Get an Event by ID."""
        response = self.request(f"/v0/events/{id}", method="GET")
        event_type = response.get('type')
        
        event_type_map = {
            'webset.created': WebsetCreatedEvent,
            'webset.deleted': WebsetDeletedEvent,
            'webset.idle': WebsetIdleEvent,
            'webset.paused': WebsetPausedEvent,
            'webset.item.created': WebsetItemCreatedEvent,
            'webset.item.enriched': WebsetItemEnrichedEvent,
            'webset.search.created': WebsetSearchCreatedEvent,
            'webset.search.updated': WebsetSearchUpdatedEvent,
            'webset.search.canceled': WebsetSearchCanceledEvent,
            'webset.search.completed': WebsetSearchCompletedEvent,
            'import.created': ImportCreatedEvent,
            'import.completed': ImportCompletedEvent,
            'monitor.created': MonitorCreatedEvent,
            'monitor.updated': MonitorUpdatedEvent,
            'monitor.deleted': MonitorDeletedEvent,
            'monitor.run.created': MonitorRunCreatedEvent,
            'monitor.run.completed': MonitorRunCompletedEvent,
        }
        
        event_class = event_type_map.get(event_type)
        if event_class:
            return event_class.model_validate(response)
        else:
            for event_class in event_type_map.values():
                try:
                    return event_class.model_validate(response)
                except Exception:
                    continue
            raise ValueError(f"Unknown event type: {event_type}")

    def list_all(self, *, limit: Optional[int] = None, types: Optional[List[EventType]] = None) -> Iterator[Event]:
        """Iterate through all Events, handling pagination automatically."""
        cursor = None
        while True:
            response = self.list(cursor=cursor, limit=limit, types=types)
            for event in response.data:
                yield event
            if not response.has_more or not response.next_cursor:
                break
            cursor = response.next_cursor

    def get_all(self, *, limit: Optional[int] = None, types: Optional[List[EventType]] = None) -> List[Event]:
        """Collect all Events into a list."""
        return list(self.list_all(limit=limit, types=types))


class AsyncEventsClient(WebsetsAsyncBaseClient):
    """Async client for managing Events."""
    
    def __init__(self, client):
        super().__init__(client)

    async def list(self, *, cursor: Optional[str] = None, limit: Optional[int] = None, 
             types: Optional[List[EventType]] = None) -> ListEventsResponse:
        """List all Events."""
        params = {}
        if cursor is not None:
            params["cursor"] = cursor
        if limit is not None:
            params["limit"] = limit
        if types is not None:
            params["types"] = [t.value if hasattr(t, 'value') else t for t in types]
            
        response = await self.request("/v0/events", params=params, method="GET")
        return ListEventsResponse.model_validate(response)

    async def get(self, id: str) -> Event:
        """Get an Event by ID."""
        response = await self.request(f"/v0/events/{id}", method="GET")
        event_type = response.get('type')
        
        event_type_map = {
            'webset.created': WebsetCreatedEvent,
            'webset.deleted': WebsetDeletedEvent,
            'webset.idle': WebsetIdleEvent,
            'webset.paused': WebsetPausedEvent,
            'webset.item.created': WebsetItemCreatedEvent,
            'webset.item.enriched': WebsetItemEnrichedEvent,
            'webset.search.created': WebsetSearchCreatedEvent,
            'webset.search.updated': WebsetSearchUpdatedEvent,
            'webset.search.canceled': WebsetSearchCanceledEvent,
            'webset.search.completed': WebsetSearchCompletedEvent,
            'import.created': ImportCreatedEvent,
            'import.completed': ImportCompletedEvent,
            'monitor.created': MonitorCreatedEvent,
            'monitor.updated': MonitorUpdatedEvent,
            'monitor.deleted': MonitorDeletedEvent,
            'monitor.run.created': MonitorRunCreatedEvent,
            'monitor.run.completed': MonitorRunCompletedEvent,
        }
        
        event_class = event_type_map.get(event_type)
        if event_class:
            return event_class.model_validate(response)
        else:
            for event_class in event_type_map.values():
                try:
                    return event_class.model_validate(response)
                except Exception:
                    continue
            raise ValueError(f"Unknown event type: {event_type}")

    async def list_all(self, *, limit: Optional[int] = None, types: Optional[List[EventType]] = None) -> AsyncIterator[Event]:
        """Iterate through all Events, handling pagination automatically."""
        cursor = None
        while True:
            response = await self.list(cursor=cursor, limit=limit, types=types)
            for event in response.data:
                yield event
            if not response.has_more or not response.next_cursor:
                break
            cursor = response.next_cursor

    async def get_all(self, *, limit: Optional[int] = None, types: Optional[List[EventType]] = None) -> List[Event]:
        """Collect all Events into a list."""
        events = []
        async for event in self.list_all(limit=limit, types=types):
            events.append(event)
        return events
