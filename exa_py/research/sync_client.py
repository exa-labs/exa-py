"""Synchronous Research API client."""

from __future__ import annotations

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
from typing_extensions import Unpack

from pydantic import BaseModel

from .base import ResearchBaseClient, raise_research_retired
from .models import (
    ResearchDto,
    ResearchEvent,
    ListResearchResponseDto,
    KnownResearchModel,
    ResearchModel,  # noqa: F401  re-exported: earlier releases imported it from here
)
# Kept importable from here: earlier releases exported these names from this module.
from .utils import (  # noqa: F401
    is_pydantic_model,
    pydantic_to_json_schema,
    stream_sse_events,
)
from ..request_options import ExtraRequestOptions, given_request_options

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
    """Client for the Research API, which has been retired.

    Every method raises ValueError without sending a request. Use the Agent API
    (``exa.agent.runs.create``) for asynchronous, multi-step research.
    """

    @overload
    def create(
        self,
        *,
        instructions: str,
        model: KnownResearchModel = "exa-research-fast",
        **extra: Unpack[ExtraRequestOptions],
    ) -> ResearchDto: ...

    @overload
    def create(
        self,
        *,
        instructions: str,
        model: KnownResearchModel = "exa-research-fast",
        output_schema: Dict[str, Any],
        **extra: Unpack[ExtraRequestOptions],
    ) -> ResearchDto: ...

    @overload
    def create(
        self,
        *,
        instructions: str,
        model: KnownResearchModel = "exa-research-fast",
        output_schema: Type[T],
        **extra: Unpack[ExtraRequestOptions],
    ) -> ResearchDto: ...

    def create(
        self,
        *,
        instructions: str,
        model: KnownResearchModel = "exa-research-fast",
        output_schema: Optional[Union[Dict[str, Any], Type[BaseModel]]] = None,
        **extra: Unpack[ExtraRequestOptions],
    ) -> ResearchDto:
        """Create a new research request.

        Args:
            instructions (str): The research instructions describing what to research.
            model (str): The model to use ('exa-research-fast', 'exa-research', or 'exa-research-pro').
            output_schema (dict): Optional JSON schema for structured output format.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).

        Returns:
            The created research object with a unique research_id.

        Examples:
            from exa_py import Exa
            import os

            exa = Exa(os.environ["EXA_API_KEY"])

            # Create a simple research task
            instructions = "What is the latest valuation of SpaceX?"
            schema = {
                "type": "object",
                "properties": {
                    "valuation": {"type": "string"},
                    "date": {"type": "string"},
                    "source": {"type": "string"}
                }
            }

            task = exa.research.create(
                instructions=instructions,
                output_schema=schema
            )

            print(f"Task created with ID: {task.research_id}")
        """
        raise_research_retired()

    @overload
    def get(
        self,
        research_id: str,
        **extra: Unpack[ExtraRequestOptions],
    ) -> ResearchDto: ...

    @overload
    def get(
        self,
        research_id: str,
        *,
        stream: Literal[False] = False,
        events: bool = False,
        **extra: Unpack[ExtraRequestOptions],
    ) -> ResearchDto: ...

    @overload
    def get(
        self,
        research_id: str,
        *,
        stream: Literal[True],
        events: Optional[bool] = None,
        **extra: Unpack[ExtraRequestOptions],
    ) -> Generator[ResearchEvent, None, None]: ...

    @overload
    def get(
        self,
        research_id: str,
        *,
        stream: Literal[False] = False,
        events: bool = False,
        output_schema: Type[T],
        **extra: Unpack[ExtraRequestOptions],
    ) -> ResearchTyped[T]: ...

    def get(
        self,
        research_id: str,
        *,
        stream: bool = False,
        events: bool = False,
        output_schema: Optional[Type[BaseModel]] = None,
        **extra: Unpack[ExtraRequestOptions],
    ) -> Union[ResearchDto, ResearchTyped, Generator[ResearchEvent, None, None]]:
        """Get a research request by ID.

        Args:
            research_id (str): The unique identifier of the research task.
            stream (bool): Whether to stream events as they occur.
            events (bool): Whether to include events in the response.
            output_schema (Type[BaseModel]): Optional Pydantic model for typed output validation.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).

        Returns:
            Research object with status and results.

        Examples:
            # Get a research task by ID
            task_id = "your-task-id-here"
            task = exa.research.get(task_id)

            print(f"Task status: {task.status}")
            if task.status == "completed":
                print(f"Results: {task.output}")
        """
        raise_research_retired()

    def list(
        self,
        *,
        cursor: Optional[str] = None,
        limit: Optional[int] = None,
        **extra: Unpack[ExtraRequestOptions],
    ) -> ListResearchResponseDto:
        """List research requests.

        Args:
            cursor (str): Pagination cursor from a previous response.
            limit (int): Maximum number of results to return.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).

        Returns:
            List of research objects with pagination info.

        Examples:
            # List all research tasks
            response = exa.research.list()
            print(f"Found {len(response.data)} tasks")

            # List with pagination
            response = exa.research.list(limit=10)
            if response.has_more:
                next_page = exa.research.list(cursor=response.next_cursor)
        """
        raise_research_retired()

    @overload
    def poll_until_finished(
        self,
        research_id: str,
        *,
        poll_interval: int = 1000,
        timeout_ms: int = 600000,
        events: bool = False,
        **extra: Unpack[ExtraRequestOptions],
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
        **extra: Unpack[ExtraRequestOptions],
    ) -> ResearchTyped[T]: ...

    def poll_until_finished(
        self,
        research_id: str,
        *,
        poll_interval: int = 1000,
        timeout_ms: int = 600000,
        events: bool = False,
        output_schema: Optional[Type[BaseModel]] = None,
        **extra: Unpack[ExtraRequestOptions],
    ) -> Union[ResearchDto, ResearchTyped]:
        """Poll until research is finished.

        Args:
            research_id (str): The unique identifier of the research task.
            poll_interval (int): Milliseconds between polling attempts.
            timeout_ms (int): Maximum time to wait in milliseconds before timing out.
            events (bool): Whether to include events in the response.
            output_schema (Type[BaseModel]): Optional Pydantic model for typed output validation.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).

        Returns:
            Completed research object with results.

        Raises:
            ValueError: Always. The Research API has been retired.

        Examples:
            # Create and poll a task until completion
            task = exa.research.create(
                instructions="Get information about Paris, France",
                output_schema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "population": {"type": "string"},
                        "founded_date": {"type": "string"}
                    }
                }
            )

            # Poll until completion
            result = exa.research.poll_until_finished(task.research_id)
            print(f"Research complete: {result.output}")
        """
        given_request_options(extra)
        raise_research_retired()
