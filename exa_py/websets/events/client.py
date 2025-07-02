from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

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
)
from ..core.base import WebsetsBaseClient

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
]

class EventsClient(WebsetsBaseClient):
    """Client for managing Events."""
    
    def __init__(self, client: Any) -> None:
        super().__init__(client)

    def list(self, *, cursor: Optional[str] = None, limit: Optional[int] = None, 
             types: Optional[List[Union[EventType, str]]] = None) -> ListEventsResponse:
        """List all Events.
        
        Args:
            cursor (str, optional): The cursor to paginate through the results.
            limit (int, optional): The number of results to return.
            types (List[EventType], optional): The types of events to filter by.
        
        Returns:
            ListEventsResponse: List of events.
        """
        params: Dict[str, Any] = {}
        if cursor is not None:
            params["cursor"] = cursor
        if limit is not None:
            params["limit"] = limit
        if types is not None:
            # Convert EventType enums to their string values
            params["types"] = [t.value if isinstance(t, EventType) else str(t) for t in types]
            
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
        event_type: Optional[str] = response.get('type')
        
        # Map event types to their corresponding classes
        event_type_map: Dict[str, type[Event]] = {
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
        }
        
        if event_type and event_type in event_type_map:
            event_class = event_type_map[event_type]
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