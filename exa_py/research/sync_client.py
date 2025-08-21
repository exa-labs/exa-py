"""Synchronous Research API client."""

from __future__ import annotations

import time
from typing import (
    Any,
    Dict,
    Generator,
    Generic,
    Literal,
    Optional,
    Type,
    TypeVar,
    Union,
    overload,
)

from pydantic import BaseModel, TypeAdapter

from .base import ResearchBaseClient
from .models import (
    ResearchDto,
    ResearchEvent,
    ListResearchResponseDto,
)
from .utils import (
    is_pydantic_model,
    pydantic_to_json_schema,
    stream_sse_events,
)

T = TypeVar("T", bound=BaseModel)


class ResearchTyped(Generic[T]):
    """Wrapper for typed research responses."""

    def __init__(self, research: ResearchDto, parsed_output: T):
        self.research = research
        self.parsed_output = parsed_output
        # Expose research fields
        self.research_id = research.research_id
        self.status = research.status
        self.created_at = research.created_at
        self.model = research.model
        self.instructions = research.instructions
        if hasattr(research, "events"):
            self.events = research.events
        if hasattr(research, "output"):
            self.output = research.output
        if hasattr(research, "cost_dollars"):
            self.cost_dollars = research.cost_dollars
        if hasattr(research, "error"):
            self.error = research.error


class ResearchClient(ResearchBaseClient):
    """Synchronous client for the Research API."""

    @overload
    def create(
        self,
        *,
        instructions: str,
        model: Literal["exa-research", "exa-research-pro"] = "exa-research",
    ) -> ResearchDto: ...

    @overload
    def create(
        self,
        *,
        instructions: str,
        model: Literal["exa-research", "exa-research-pro"] = "exa-research",
        output_schema: Dict[str, Any],
    ) -> ResearchDto: ...

    @overload
    def create(
        self,
        *,
        instructions: str,
        model: Literal["exa-research", "exa-research-pro"] = "exa-research",
        output_schema: Type[T],
    ) -> ResearchDto: ...

    def create(
        self,
        *,
        instructions: str,
        model: Literal["exa-research", "exa-research-pro"] = "exa-research",
        output_schema: Optional[Union[Dict[str, Any], Type[BaseModel]]] = None,
    ) -> ResearchDto:
        """Create a new research request.

        Args:
            instructions: The research instructions.
            model: The model to use for research.
            output_schema: Optional JSON schema or Pydantic model for structured output.

        Returns:
            The created research object.
        """
        payload = {
            "instructions": instructions,
            "model": model,
        }

        if output_schema is not None:
            if is_pydantic_model(output_schema):
                payload["outputSchema"] = pydantic_to_json_schema(output_schema)
            else:
                payload["outputSchema"] = output_schema

        response = self.request("", method="POST", data=payload)
        adapter = TypeAdapter(ResearchDto)
        return adapter.validate_python(response)

    @overload
    def get(
        self,
        research_id: str,
    ) -> ResearchDto: ...

    @overload
    def get(
        self,
        research_id: str,
        *,
        stream: Literal[False] = False,
        events: bool = False,
    ) -> ResearchDto: ...

    @overload
    def get(
        self,
        research_id: str,
        *,
        stream: Literal[True],
        events: Optional[bool] = None,
    ) -> Generator[ResearchEvent, None, None]: ...

    @overload
    def get(
        self,
        research_id: str,
        *,
        stream: Literal[False] = False,
        events: bool = False,
        output_schema: Type[T],
    ) -> ResearchTyped[T]: ...

    def get(
        self,
        research_id: str,
        *,
        stream: bool = False,
        events: bool = False,
        output_schema: Optional[Type[BaseModel]] = None,
    ) -> Union[ResearchDto, ResearchTyped, Generator[ResearchEvent, None, None]]:
        """Get a research request by ID.

        Args:
            research_id: The research ID.
            stream: Whether to stream events.
            events: Whether to include events in non-streaming response.
            output_schema: Optional Pydantic model for typed output validation.

        Returns:
            Research object, typed research, or event generator.
        """
        params = {}
        if not stream:
            params["stream"] = "false"
            if events:
                params["events"] = "true"
        else:
            params["stream"] = "true"
            if events is not None:
                params["events"] = str(events).lower()

        if stream:
            response = self.request(
                f"/{research_id}", method="GET", params=params, stream=True
            )
            return stream_sse_events(response)
        else:
            response = self.request(f"/{research_id}", method="GET", params=params)
            adapter = TypeAdapter(ResearchDto)
            research = adapter.validate_python(response)

            if output_schema and hasattr(research, "output") and research.output:
                try:
                    if research.output.parsed:
                        parsed = output_schema.model_validate(research.output.parsed)
                    else:
                        import json

                        parsed_data = json.loads(research.output.content)
                        parsed = output_schema.model_validate(parsed_data)
                    return ResearchTyped(research, parsed)
                except Exception:
                    # If parsing fails, return the regular research object
                    return research

            return research

    def list(
        self,
        *,
        cursor: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> ListResearchResponseDto:
        """List research requests.

        Args:
            cursor: Pagination cursor.
            limit: Maximum number of results.

        Returns:
            List of research objects with pagination info.
        """
        params = self.build_pagination_params(cursor, limit)
        response = self.request("", method="GET", params=params)
        return ListResearchResponseDto.model_validate(response)

    @overload
    def poll_until_finished(
        self,
        research_id: str,
        *,
        poll_interval: int = 1000,
        timeout_ms: int = 600000,
        events: bool = False,
    ) -> ResearchDto: ...

    @overload
    def poll_until_finished(
        self,
        research_id: str,
        *,
        poll_interval: int = 1000,
        timeout_ms: int = 600000,
        events: bool = False,
        output_schema: Type[T],
    ) -> ResearchTyped[T]: ...

    def poll_until_finished(
        self,
        research_id: str,
        *,
        poll_interval: int = 1000,
        timeout_ms: int = 600000,
        events: bool = False,
        output_schema: Optional[Type[BaseModel]] = None,
    ) -> Union[ResearchDto, ResearchTyped]:
        """Poll until research is finished.

        Args:
            research_id: The research ID.
            poll_interval: Milliseconds between polls (default 1000).
            timeout_ms: Maximum time to wait in milliseconds (default 600000).
            events: Whether to include events in the response.
            output_schema: Optional Pydantic model for typed output validation.

        Returns:
            Completed research object or typed research.

        Raises:
            TimeoutError: If research doesn't complete within timeout.
            RuntimeError: If polling fails too many times.
        """
        poll_interval_sec = poll_interval / 1000
        timeout_sec = timeout_ms / 1000
        max_consecutive_failures = 5
        start_time = time.time()
        consecutive_failures = 0

        while True:
            try:
                if output_schema:
                    result = self.get(
                        research_id, events=events, output_schema=output_schema
                    )
                else:
                    result = self.get(research_id, events=events)

                consecutive_failures = 0

                # Check if research is finished
                status = result.status if hasattr(result, "status") else None
                if status in ["completed", "failed", "canceled"]:
                    return result

            except Exception as e:
                consecutive_failures += 1
                if consecutive_failures >= max_consecutive_failures:
                    raise RuntimeError(
                        f"Polling failed {max_consecutive_failures} times in a row "
                        f"for research {research_id}: {e}"
                    )

            if time.time() - start_time > timeout_sec:
                raise TimeoutError(
                    f"Research {research_id} did not complete within {timeout_ms}ms"
                )

            time.sleep(poll_interval_sec)
