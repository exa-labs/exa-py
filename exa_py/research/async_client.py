"""Asynchronous Research API client."""

from __future__ import annotations

from typing import (
    Any,
    AsyncGenerator,
    Dict,
    Generic,
    Literal,
    Optional,
    Type,
    TypeVar,
    Union,
    overload,
)
from typing_extensions import Unpack

from pydantic import BaseModel, TypeAdapter

from .base import AsyncResearchBaseClient, raise_research_retired
from .models import (
    ResearchDto,
    ResearchEvent,
    ListResearchResponseDto,
    KnownResearchModel,
    ResearchModel,  # noqa: F401  re-exported: earlier releases imported it from here
)
from .utils import (
    async_stream_sse_events,
    is_pydantic_model,
    pydantic_to_json_schema,
)
from ..request_options import ExtraRequestOptions, given_request_options

T = TypeVar("T", bound=BaseModel)


class AsyncResearchTyped(Generic[T]):
    """Wrapper for typed research responses in async context."""

    def __init__(self, research: ResearchDto, parsed_output: T):
        self.research = research
        self.parsed_output = parsed_output
        # Expose research fields
        self.research_id = research.research_id
        self.status = research.status
        self.created_at = research.created_at
        self.model = research.model
        self.instructions = research.instructions
        self.output_schema = research.output_schema
        if hasattr(research, "events"):
            self.events = research.events
        if hasattr(research, "output"):
            self.output = research.output
        if hasattr(research, "cost_dollars"):
            self.cost_dollars = research.cost_dollars
        if hasattr(research, "error"):
            self.error = research.error


class AsyncResearchClient(AsyncResearchBaseClient):
    """Client for the Research API, which has been retired.

    Every method raises ValueError without sending a request. Use the Agent API
    (``exa.agent.runs.create``) for asynchronous, multi-step research.
    """

    @overload
    async def create(
        self,
        *,
        instructions: str,
        model: KnownResearchModel = "exa-research-fast",
        **extra: Unpack[ExtraRequestOptions],
    ) -> ResearchDto: ...

    @overload
    async def create(
        self,
        *,
        instructions: str,
        model: Literal["exa-research", "exa-research-pro"] = "exa-research",
        output_schema: Dict[str, Any],
        **extra: Unpack[ExtraRequestOptions],
    ) -> ResearchDto: ...

    @overload
    async def create(
        self,
        *,
        instructions: str,
        model: Literal["exa-research", "exa-research-pro"] = "exa-research",
        output_schema: Type[T],
        **extra: Unpack[ExtraRequestOptions],
    ) -> ResearchDto: ...

    async def create(
        self,
        *,
        instructions: str,
        model: Literal["exa-research", "exa-research-pro"] = "exa-research",
        output_schema: Optional[Union[Dict[str, Any], Type[BaseModel]]] = None,
        **extra: Unpack[ExtraRequestOptions],
    ) -> ResearchDto:
        """Create a new research request.

        Args:
            instructions: The research instructions.
            model: The model to use for research.
            output_schema: Optional JSON schema or Pydantic model for structured output.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).

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

        response = await self.request("", method="POST", data=payload, **extra)
        adapter = TypeAdapter(ResearchDto)
        return adapter.validate_python(response)

    @overload
    async def get(
        self,
        research_id: str,
        **extra: Unpack[ExtraRequestOptions],
    ) -> ResearchDto: ...

    @overload
    async def get(
        self,
        research_id: str,
        *,
        stream: Literal[False] = False,
        events: bool = False,
        **extra: Unpack[ExtraRequestOptions],
    ) -> ResearchDto: ...

    @overload
    async def get(
        self,
        research_id: str,
        *,
        stream: Literal[True],
        events: Optional[bool] = None,
        **extra: Unpack[ExtraRequestOptions],
    ) -> AsyncGenerator[ResearchEvent, None]: ...

    @overload
    async def get(
        self,
        research_id: str,
        *,
        stream: Literal[False] = False,
        events: bool = False,
        output_schema: Type[T],
        **extra: Unpack[ExtraRequestOptions],
    ) -> AsyncResearchTyped[T]: ...

    async def get(
        self,
        research_id: str,
        *,
        stream: bool = False,
        events: bool = False,
        output_schema: Optional[Type[BaseModel]] = None,
        **extra: Unpack[ExtraRequestOptions],
    ) -> Union[ResearchDto, AsyncResearchTyped, AsyncGenerator[ResearchEvent, None]]:
        """Get a research request by ID.

        Args:
            research_id: The research ID.
            stream: Whether to stream events.
            events: Whether to include events in non-streaming response.
            output_schema: Optional Pydantic model for typed output validation.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).

        Returns:
            Research object, typed research, or async event generator.
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
            response = await self.request(
                f"/{research_id}", method="GET", params=params, stream=True,
                **extra,
            )
            return async_stream_sse_events(response)
        else:
            response = await self.request(
                f"/{research_id}", method="GET", params=params,
                **extra,
            )
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
                    return AsyncResearchTyped(research, parsed)
                except Exception:
                    # If parsing fails, return the regular research object
                    return research

            return research

    async def list(
        self,
        *,
        cursor: Optional[str] = None,
        limit: Optional[int] = None,
        **extra: Unpack[ExtraRequestOptions],
    ) -> ListResearchResponseDto:
        """List research requests.

        Args:
            cursor: Pagination cursor.
            limit: Maximum number of results.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).

        Returns:
            List of research objects with pagination info.
        """
        params = self.build_pagination_params(cursor, limit)
        response = await self.request("", method="GET", params=params, **extra)
        return ListResearchResponseDto.model_validate(response)

    @overload
    async def poll_until_finished(
        self,
        research_id: str,
        *,
        poll_interval: int = 1000,
        timeout_ms: int = 600000,
        events: bool = False,
        **extra: Unpack[ExtraRequestOptions],
    ) -> ResearchDto: ...

    @overload
    async def poll_until_finished(
        self,
        research_id: str,
        *,
        poll_interval: int = 1000,
        timeout_ms: int = 600000,
        events: bool = False,
        output_schema: Type[T],
        **extra: Unpack[ExtraRequestOptions],
    ) -> AsyncResearchTyped[T]: ...

    async def poll_until_finished(
        self,
        research_id: str,
        *,
        poll_interval: int = 1000,
        timeout_ms: int = 600000,
        events: bool = False,
        output_schema: Optional[Type[BaseModel]] = None,
        **extra: Unpack[ExtraRequestOptions],
    ) -> Union[ResearchDto, AsyncResearchTyped]:
        """Poll until research is finished.

        Args:
            research_id: The research ID.
            poll_interval: Milliseconds between polls (default 1000).
            timeout_ms: Maximum time to wait in milliseconds (default 600000).
            events: Whether to include events in the response.
            output_schema: Optional Pydantic model for typed output validation.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).

        Returns:
            Completed research object or typed research.

        Raises:
            ValueError: Always. The Research API has been retired.
        """
        given_request_options(extra)
        raise_research_retired()
