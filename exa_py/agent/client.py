"""Synchronous Exa Agent API client."""

from __future__ import annotations

import time
from typing import (
    Any,
    Dict,
    Generator,
    Iterator,
    Literal,
    Optional,
    Sequence,
    Type,
    Union,
    overload,
)

from pydantic import BaseModel

from exa_py.utils import _convert_schema_input

from .base import AgentBaseClient
from .types import (
    AgentEvent,
    AgentEffort,
    AgentInput,
    AgentRun,
    CreateAgentRunParams,
    DeletedAgentRun,
    ListAgentRunEventsResponse,
    ListAgentRunsResponse,
)
from .utils import stream_agent_events


def _is_pydantic_model(schema: Any) -> bool:
    try:
        return isinstance(schema, type) and issubclass(schema, BaseModel)
    except TypeError:
        return False


class AgentRunEventsClient(AgentBaseClient):
    """Synchronous client for Agent run events."""

    def list(
        self,
        run_id: str,
        *,
        betas: Sequence[str],
        cursor: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> ListAgentRunEventsResponse:
        """List stored events for an Agent run.

        Args:
            run_id: The ID of the Agent run.
            betas: Beta feature identifiers to enable for this request.
            cursor: Pagination cursor from a previous response.
            limit: Maximum number of events to return.

        Returns:
            List of Agent run events with pagination info.

        Examples:
            from exa_py import Exa

            exa = Exa("EXA_API_KEY")

            events = exa.beta.agent.runs.events.list(
                "agent_run_123",
                betas=["agent-2026-05-07"],
                limit=20,
            )
            print(events.data[0].event if events.data else "no events yet")
        """
        params = self.build_pagination_params(cursor, limit)
        response = self.request(
            f"/{run_id}/events", betas=betas, method="GET", params=params
        )
        return ListAgentRunEventsResponse.model_validate(response)


class AgentRunsClient(AgentBaseClient):
    """Synchronous client for Agent runs."""

    events: AgentRunEventsClient

    def __init__(self, client: Any):
        super().__init__(client)
        self.events = AgentRunEventsClient(client)

    @overload
    def create(
        self,
        *,
        betas: Sequence[str],
        query: str,
        system_prompt: Optional[str] = None,
        input: Optional[Union[Dict[str, Any], AgentInput]] = None,
        output_schema: Optional[Union[Dict[str, Any], Type[BaseModel]]] = None,
        effort: Optional[AgentEffort] = None,
        previous_run_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        stream: Literal[False] = False,
    ) -> AgentRun: ...

    @overload
    def create(
        self,
        *,
        betas: Sequence[str],
        query: str,
        system_prompt: Optional[str] = None,
        input: Optional[Union[Dict[str, Any], AgentInput]] = None,
        output_schema: Optional[Union[Dict[str, Any], Type[BaseModel]]] = None,
        effort: Optional[AgentEffort] = None,
        previous_run_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        stream: Literal[True] = True,
    ) -> Generator[AgentEvent, None, None]: ...

    def create(
        self,
        *,
        betas: Sequence[str],
        query: str,
        system_prompt: Optional[str] = None,
        input: Optional[Union[Dict[str, Any], AgentInput]] = None,
        output_schema: Optional[Union[Dict[str, Any], Type[BaseModel]]] = None,
        effort: Optional[AgentEffort] = None,
        previous_run_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        stream: bool = False,
    ) -> Union[AgentRun, Generator[AgentEvent, None, None]]:
        """Create an Agent run.

        Args:
            betas: Beta feature identifiers to enable for this request.
            query: The task or question for the Agent run.
            system_prompt: Optional instructions that steer the Agent.
            input: Optional structured input data for the Agent.
            output_schema: Optional JSON schema or Pydantic model for structured output.
            effort: Optional cost and reasoning effort preference. Defaults to auto.
            previous_run_id: Optional prior run ID to continue from.
            metadata: Optional metadata to attach to the run.
            stream: Whether to stream server-sent Agent events instead of returning a run.

        Returns:
            The created Agent run, or a generator of Agent events when stream is True.

        Examples:
            from exa_py import Exa

            exa = Exa("EXA_API_KEY")

            run = exa.beta.agent.runs.create(
                betas=["agent-2026-05-07"],
                query="Find companies building browser automation tools",
            )
            print(run.id)
        """
        schema = (
            _convert_schema_input(output_schema)
            if _is_pydantic_model(output_schema)
            else output_schema
        )
        run_input = (
            input
            if isinstance(input, AgentInput) or input is None
            else AgentInput.model_validate(input)
        )
        payload = CreateAgentRunParams(
            query=query,
            system_prompt=system_prompt,
            input=run_input,
            output_schema=schema,
            effort=effort,
            previous_run_id=previous_run_id,
            metadata=metadata,
        ).model_dump(by_alias=True, exclude_none=True)

        response = self.request(
            "", betas=betas, method="POST", data=payload, stream=stream
        )
        if stream:
            return stream_agent_events(response)
        return AgentRun.model_validate(response)

    def get(self, run_id: str, *, betas: Sequence[str]) -> AgentRun:
        """Get an Agent run by ID.

        Args:
            run_id: The ID of the Agent run.
            betas: Beta feature identifiers to enable for this request.

        Returns:
            The Agent run.

        Examples:
            from exa_py import Exa

            exa = Exa("EXA_API_KEY")

            run = exa.beta.agent.runs.get(
                "agent_run_123",
                betas=["agent-2026-05-07"],
            )
            print(run.status)
        """
        response = self.request(f"/{run_id}", betas=betas, method="GET")
        return AgentRun.model_validate(response)

    def list(
        self,
        *,
        betas: Sequence[str],
        cursor: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> ListAgentRunsResponse:
        """List Agent runs.

        Args:
            betas: Beta feature identifiers to enable for this request.
            cursor: Pagination cursor from a previous response.
            limit: Maximum number of runs to return.

        Returns:
            List of Agent runs with pagination info.

        Examples:
            from exa_py import Exa

            exa = Exa("EXA_API_KEY")

            runs = exa.beta.agent.runs.list(
                betas=["agent-2026-05-07"],
                limit=10,
            )
            print([run.id for run in runs.data])
        """
        params = self.build_pagination_params(cursor, limit)
        response = self.request("", betas=betas, method="GET", params=params)
        return ListAgentRunsResponse.model_validate(response)

    def list_all(
        self, *, betas: Sequence[str], limit: Optional[int] = None
    ) -> Iterator[AgentRun]:
        """Iterate through all Agent runs, handling pagination automatically.

        Args:
            betas: Beta feature identifiers to enable for this request.
            limit: Maximum number of runs to return per page.

        Yields:
            AgentRun: Each Agent run.

        Examples:
            from exa_py import Exa

            exa = Exa("EXA_API_KEY")

            for run in exa.beta.agent.runs.list_all(
                betas=["agent-2026-05-07"],
            ):
                print(run.id)
        """
        cursor = None
        while True:
            response = self.list(betas=betas, cursor=cursor, limit=limit)
            for run in response.data:
                yield run
            if not response.has_more or not response.next_cursor:
                break
            cursor = response.next_cursor

    def get_all(
        self, *, betas: Sequence[str], limit: Optional[int] = None
    ) -> list[AgentRun]:
        """Collect all Agent runs into a list.

        Args:
            betas: Beta feature identifiers to enable for this request.
            limit: Maximum number of runs to return per page.

        Returns:
            List of all Agent runs.

        Examples:
            from exa_py import Exa

            exa = Exa("EXA_API_KEY")

            runs = exa.beta.agent.runs.get_all(
                betas=["agent-2026-05-07"],
            )
            print(len(runs))
        """
        return list(self.list_all(betas=betas, limit=limit))

    def cancel(self, run_id: str, *, betas: Sequence[str]) -> AgentRun:
        """Cancel a queued or running Agent run.

        Args:
            run_id: The ID of the Agent run.
            betas: Beta feature identifiers to enable for this request.

        Returns:
            The cancelled Agent run.

        Examples:
            from exa_py import Exa

            exa = Exa("EXA_API_KEY")

            run = exa.beta.agent.runs.cancel(
                "agent_run_123",
                betas=["agent-2026-05-07"],
            )
            print(run.status)
        """
        response = self.request(f"/{run_id}/cancel", betas=betas, method="POST")
        return AgentRun.model_validate(response)

    def delete(self, run_id: str, *, betas: Sequence[str]) -> DeletedAgentRun:
        """Delete an Agent run.

        Args:
            run_id: The ID of the Agent run.
            betas: Beta feature identifiers to enable for this request.

        Returns:
            Deletion status for the Agent run.

        Examples:
            from exa_py import Exa

            exa = Exa("EXA_API_KEY")

            deleted = exa.beta.agent.runs.delete(
                "agent_run_123",
                betas=["agent-2026-05-07"],
            )
            print(deleted.deleted)
        """
        response = self.request(f"/{run_id}", betas=betas, method="DELETE")
        return DeletedAgentRun.model_validate(response)

    def poll_until_finished(
        self,
        run_id: str,
        *,
        betas: Sequence[str],
        poll_interval: int = 1000,
        timeout_ms: int = 3600000,
    ) -> AgentRun:
        """Poll an Agent run until it reaches a terminal status.

        Args:
            run_id: The ID of the Agent run.
            betas: Beta feature identifiers to enable for this request.
            poll_interval: Delay between polls in milliseconds.
            timeout_ms: Maximum time to wait in milliseconds.

        Returns:
            The terminal Agent run.

        Examples:
            from exa_py import Exa

            exa = Exa("EXA_API_KEY")

            run = exa.beta.agent.runs.poll_until_finished(
                "agent_run_123",
                betas=["agent-2026-05-07"],
            )
            print(run.status)
        """
        start_time = time.monotonic()
        poll_interval_sec = poll_interval / 1000

        while True:
            run = self.get(run_id, betas=betas)
            if run.status in ("completed", "failed", "cancelled"):
                return run

            if (time.monotonic() - start_time) * 1000 > timeout_ms:
                raise TimeoutError(
                    f"Agent run {run_id} did not complete within {timeout_ms}ms"
                )

            time.sleep(poll_interval_sec)


class AgentBetaNamespace:
    """Synchronous beta Agent namespace."""

    runs: AgentRunsClient

    def __init__(self, client: Any):
        self.runs = AgentRunsClient(client)


class BetaClient:
    """Synchronous beta namespace."""

    agent: AgentBetaNamespace

    def __init__(self, client: Any):
        self.agent = AgentBetaNamespace(client)
