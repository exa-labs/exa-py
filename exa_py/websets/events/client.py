from __future__ import annotations

from typing import List, Optional, Union

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
        """List all Events.
        
        Args:
            cursor (str, optional): The cursor to paginate through the results.
            limit (int, optional): The number of results to return.
            types (List[EventType], optional): The types of events to filter by.
        
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
            
        response = self.request("/v0/events", params=params, method="GET")
        return ListEventsResponse.model_validate(response)

    def get(self, id: str) -> Event:
        """Get an Event by ID.
        
        Args:
            id (str): The ID of the Event.
        
        Returns:
            Event: The retrieved event.
        """
        response = self.request(f"/v0/events/{id}", method="GET")
        
        # The response should contain a 'type' field that helps us determine
        # which specific event class to use for validation
        event_type = response.get('type')
        
        # Map event types to their corresponding classes
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
            # Fallback - try each type until one validates
            # This shouldn't happen in normal operation
            for event_class in event_type_map.values():
                try:
                    return event_class.model_validate(response)
                except Exception:
                    continue
            
            raise ValueError(f"Unknown event type: {event_type}")


class AsyncEventsClient(WebsetsAsyncBaseClient):
    """Async client for managing Events."""
    
    def __init__(self, client):
        super().__init__(client)

    async def list(self, *, cursor: Optional[str] = None, limit: Optional[int] = None, 
             types: Optional[List[EventType]] = None) -> ListEventsResponse:
        """List all Events.
        
        Args:
            cursor (str, optional): The cursor to paginate through the results.
            limit (int, optional): The number of results to return.
            types (List[EventType], optional): The types of events to filter by.
        
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
            
        response = await self.request("/v0/events", params=params, method="GET")
        return ListEventsResponse.model_validate(response)

    async def get(self, id: str) -> Event:
        """Get an Event by ID.
        
        Args:
            id (str): The ID of the Event.
        
        Returns:
            Event: The retrieved event.
        """
        response = await self.request(f"/v0/events/{id}", method="GET")
        
        # The response should contain a 'type' field that helps us determine
        # which specific event class to use for validation
        event_type = response.get('type')
        
        # Map event types to their corresponding classes
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
            # Fallback - try each type until one validates
            # This shouldn't happen in normal operation
            for event_class in event_type_map.values():
                try:
                    return event_class.model_validate(response)
                except Exception:
                    continue
            
            raise ValueError(f"Unknown event type: {event_type}")