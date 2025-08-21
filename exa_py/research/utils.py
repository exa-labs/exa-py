"""Utilities for the Research API."""

from __future__ import annotations

import json
from typing import (
    Any,
    AsyncGenerator,
    Dict,
    Generator,
    Optional,
    Type,
)

import httpx
import requests
from pydantic import BaseModel, ValidationError

from .models import (
    ResearchEvent,
    ResearchDefinitionEvent,
    ResearchOutputEvent,
    ResearchPlanDefinitionEvent,
    ResearchPlanOperationEvent,
    ResearchPlanOutputEvent,
    ResearchTaskDefinitionEvent,
    ResearchTaskOperationEvent,
    ResearchTaskOutputEvent,
)


def is_pydantic_model(schema: Any) -> bool:
    """Check if the given schema is a Pydantic model class.

    Args:
        schema: The schema to check.

    Returns:
        True if schema is a Pydantic model class, False otherwise.
    """
    try:
        return isinstance(schema, type) and issubclass(schema, BaseModel)
    except (TypeError, AttributeError):
        return False


def pydantic_to_json_schema(model: Type[BaseModel]) -> Dict[str, Any]:
    """Convert a Pydantic model to JSON Schema.

    Args:
        model: The Pydantic model class.

    Returns:
        JSON Schema dictionary with all references inlined.
    """
    # Import here to avoid circular imports
    from exa_py.utils import _convert_schema_input

    # Use the existing _convert_schema_input which already handles inlining
    return _convert_schema_input(model)


def parse_sse_line(line: str) -> Optional[tuple[str, str]]:
    """Parse a single SSE line.

    Args:
        line: The SSE line to parse.

    Returns:
        Tuple of (field, value) or None if not a valid SSE line.
    """
    if not line or not line.strip():
        return None

    if ":" not in line:
        return None

    field, _, value = line.partition(":")
    return field.strip(), value.strip()


def parse_sse_event_raw(event_lines: list[str]) -> Optional[Dict[str, Any]]:
    """Parse SSE event lines into a raw event dictionary.

    Args:
        event_lines: List of lines that make up an SSE event.

    Returns:
        Parsed event data or None if invalid.
    """
    event_name = None
    event_data = None

    for line in event_lines:
        parsed = parse_sse_line(line)
        if not parsed:
            continue

        field, value = parsed
        if field == "event":
            event_name = value
        elif field == "data":
            try:
                event_data = json.loads(value)
            except json.JSONDecodeError:
                # Some events might have non-JSON data
                event_data = value

    if event_name and event_data:
        # Add eventType to the data for consistency
        if isinstance(event_data, dict):
            event_data["eventType"] = event_name
        return event_data

    return None


def parse_research_event(raw_event: Dict[str, Any]) -> Optional[ResearchEvent]:
    """Parse a raw event dictionary into a typed ResearchEvent.

    Args:
        raw_event: Raw event dictionary with eventType field.

    Returns:
        Typed ResearchEvent or None if parsing fails.
    """
    event_type = raw_event.get("eventType")
    if not event_type:
        return None

    # Map event types to their corresponding Pydantic models
    event_models = {
        "research-definition": ResearchDefinitionEvent,
        "research-output": ResearchOutputEvent,
        "plan-definition": ResearchPlanDefinitionEvent,
        "plan-operation": ResearchPlanOperationEvent,
        "plan-output": ResearchPlanOutputEvent,
        "task-definition": ResearchTaskDefinitionEvent,
        "task-operation": ResearchTaskOperationEvent,
        "task-output": ResearchTaskOutputEvent,
    }

    model_class = event_models.get(event_type)
    if not model_class:
        return None

    try:
        return model_class.model_validate(raw_event)
    except ValidationError:
        # Log or handle validation error if needed
        return None


def stream_sse_events(
    response: requests.Response,
) -> Generator[ResearchEvent, None, None]:
    """Stream SSE events from a requests Response.

    Args:
        response: The streaming response object.

    Yields:
        Parsed ResearchEvent objects.
    """
    event_lines = []

    for line in response.iter_lines():
        if not line:
            # Empty line signals end of event
            if event_lines:
                raw_event = parse_sse_event_raw(event_lines)
                if raw_event:
                    event = parse_research_event(raw_event)
                    if event:
                        yield event
                event_lines = []
        else:
            decoded_line = line.decode("utf-8") if isinstance(line, bytes) else line
            event_lines.append(decoded_line)

    # Handle any remaining lines
    if event_lines:
        raw_event = parse_sse_event_raw(event_lines)
        if raw_event:
            event = parse_research_event(raw_event)
            if event:
                yield event


async def async_stream_sse_events(
    response: httpx.Response,
) -> AsyncGenerator[ResearchEvent, None]:
    """Stream SSE events from an httpx Response.

    Args:
        response: The async streaming response object.

    Yields:
        Parsed ResearchEvent objects.
    """
    event_lines = []

    async for line in response.aiter_lines():
        if not line:
            # Empty line signals end of event
            if event_lines:
                raw_event = parse_sse_event_raw(event_lines)
                if raw_event:
                    event = parse_research_event(raw_event)
                    if event:
                        yield event
                event_lines = []
        else:
            event_lines.append(line)

    # Handle any remaining lines
    if event_lines:
        raw_event = parse_sse_event_raw(event_lines)
        if raw_event:
            event = parse_research_event(raw_event)
            if event:
                yield event
