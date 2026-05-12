"""Utilities for the Exa Agent API."""

from __future__ import annotations

import json
from typing import Any, AsyncGenerator, Dict, Generator, Optional

import httpx
import requests

from .types import AgentEvent


def parse_sse_event_lines(event_lines: list[str]) -> Optional[AgentEvent]:
    event_id = None
    event_name = None
    data_lines = []

    for line in event_lines:
        if not line or ":" not in line:
            continue

        field, _, value = line.partition(":")
        value = value[1:] if value.startswith(" ") else value

        if field == "id":
            event_id = value
        elif field == "event":
            event_name = value
        elif field == "data":
            data_lines.append(value)

    if not event_name or not data_lines:
        return None

    raw_data = "\n".join(data_lines)
    try:
        data: Dict[str, Any] = json.loads(raw_data)
    except json.JSONDecodeError:
        data = {"value": raw_data}

    return AgentEvent(id=event_id, event=event_name, data=data)


def stream_agent_events(response: requests.Response) -> Generator[AgentEvent, None, None]:
    event_lines: list[str] = []

    try:
        for line in response.iter_lines():
            if not line:
                if event_lines:
                    event = parse_sse_event_lines(event_lines)
                    if event:
                        yield event
                    event_lines = []
            else:
                decoded = line.decode("utf-8") if isinstance(line, bytes) else line
                event_lines.append(decoded)

        if event_lines:
            event = parse_sse_event_lines(event_lines)
            if event:
                yield event
    finally:
        close = getattr(response, "close", None)
        if close:
            close()


async def async_stream_agent_events(
    response: httpx.Response,
) -> AsyncGenerator[AgentEvent, None]:
    event_lines: list[str] = []

    try:
        async for line in response.aiter_lines():
            if not line:
                if event_lines:
                    event = parse_sse_event_lines(event_lines)
                    if event:
                        yield event
                    event_lines = []
            else:
                event_lines.append(line)

        if event_lines:
            event = parse_sse_event_lines(event_lines)
            if event:
                yield event
    finally:
        aclose = getattr(response, "aclose", None)
        if aclose:
            await aclose()
