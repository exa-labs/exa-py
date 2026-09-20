"""Asynchronous Exa Agent Monitors API client."""

from __future__ import annotations

import asyncio
import time
from typing import Any, AsyncIterator, Dict, Optional, Sequence

from .async_base import AsyncAgentMonitorsBaseClient
from .client import (
    EntityInput,
    FieldInput,
    _ensure_completed_backtest,
    _serialize_entities,
    _serialize_fields,
)
from .types import (
    AgentMonitor,
    AgentMonitorChange,
    AgentMonitorEntityView,
    AgentMonitorBacktest,
    DeletedAgentMonitor,
    ListAgentMonitorChangesResponse,
    ListAgentMonitorEntitiesResponse,
    ListAgentMonitorsResponse,
)

_DEFAULT_BACKTEST_POLL_INTERVAL_MS = 2000
_DEFAULT_BACKTEST_POLL_TIMEOUT_MS = 3600000


class AsyncAgentMonitorEntitiesClient(AsyncAgentMonitorsBaseClient):
    """Asynchronous client for an Agent Monitor's entities."""

    async def add(
        self,
        monitor_id: str,
        *,
        betas: Sequence[str],
        entities: Sequence[EntityInput],
    ) -> AgentMonitor:
        """Add entities to an existing Agent Monitor.

        Added entities are resolved and backfilled shortly after the request
        completes, then update on the monitor's regular refresh cadence.

        Args:
            betas: Beta feature identifiers to enable for this request.
            monitor_id: The ID of the Agent Monitor.
            entities: Entities to add, each with a name and a unique domain.

        Returns:
            The updated Agent Monitor.

        Examples:
            from exa_py import AsyncExa
            from exa_py.agent import AGENT_MONITORS_BETA_HEADER

            exa = AsyncExa("EXA_API_KEY")

            monitor = await exa.beta.agent.monitors.entities.add(
                "agentmon_123",
                betas=[AGENT_MONITORS_BETA_HEADER],
                entities=[{"name": "Initech", "domain": "initech.com"}],
            )
            print(monitor.entity_count)
        """
        payload = {"entities": _serialize_entities(entities)}
        response = await self.request(
            f"/{monitor_id}/entities", betas=betas, method="POST", data=payload
        )
        return AgentMonitor.model_validate(response)

    async def list(
        self,
        monitor_id: str,
        *,
        betas: Sequence[str],
        cursor: Optional[str] = None,
        limit: Optional[int] = None,
        since: Optional[str] = None,
    ) -> ListAgentMonitorEntitiesResponse:
        """Page an Agent Monitor's current entities and contents.

        Args:
            betas: Beta feature identifiers to enable for this request.
            monitor_id: The ID of the Agent Monitor.
            cursor: Pagination cursor from a previous response.
            limit: Maximum number of entities to return.
            since: Only return entities whose contents were updated at or
                after this ISO-8601 timestamp.

        Returns:
            One page of entities with their contents keyed by field ID.

        Examples:
            from exa_py import AsyncExa
            from exa_py.agent import AGENT_MONITORS_BETA_HEADER

            exa = AsyncExa("EXA_API_KEY")

            page = await exa.beta.agent.monitors.entities.list("agentmon_123", betas=[AGENT_MONITORS_BETA_HEADER], limit=50)
            for view in page.data:
                print(view.entity.name, view.contents)
        """
        params = self.build_pagination_params(cursor, limit, since)
        response = await self.request(
            f"/{monitor_id}/entities", betas=betas, method="GET", params=params
        )
        return ListAgentMonitorEntitiesResponse.model_validate(response)

    async def list_all(
        self,
        monitor_id: str,
        *,
        betas: Sequence[str],
        cursor: Optional[str] = None,
        limit: Optional[int] = None,
        since: Optional[str] = None,
    ) -> AsyncIterator[AgentMonitorEntityView]:
        """Iterate through all of a monitor's entities, handling pagination automatically.

        Args:
            betas: Beta feature identifiers to enable for this request.
            monitor_id: The ID of the Agent Monitor.
            cursor: Entities cursor to resume from.
            limit: Maximum number of entities to return per page.
            since: Only return entities whose contents were updated at or
                after this ISO-8601 timestamp.

        Yields:
            AgentMonitorEntityView: Each entity with its contents.

        Examples:
            from exa_py import AsyncExa
            from exa_py.agent import AGENT_MONITORS_BETA_HEADER

            exa = AsyncExa("EXA_API_KEY")

            async for view in exa.beta.agent.monitors.entities.list_all("agentmon_123", betas=[AGENT_MONITORS_BETA_HEADER]):
                print(view.entity.name)
        """
        while True:
            response = await self.list(
                monitor_id,
                betas=betas,
                cursor=cursor,
                limit=limit,
                since=since,
            )
            for entity_view in response.data:
                yield entity_view
            if not response.has_more or not response.next_cursor:
                break
            cursor = response.next_cursor

    async def get_all(
        self,
        monitor_id: str,
        *,
        betas: Sequence[str],
        cursor: Optional[str] = None,
        limit: Optional[int] = None,
        since: Optional[str] = None,
    ) -> list[AgentMonitorEntityView]:
        """Collect all of a monitor's entities into a list.

        Args:
            betas: Beta feature identifiers to enable for this request.
            monitor_id: The ID of the Agent Monitor.
            cursor: Entities cursor to resume from.
            limit: Maximum number of entities to return per page.
            since: Only return entities whose contents were updated at or
                after this ISO-8601 timestamp.

        Returns:
            List of all entities with their contents.

        Examples:
            from exa_py import AsyncExa
            from exa_py.agent import AGENT_MONITORS_BETA_HEADER

            exa = AsyncExa("EXA_API_KEY")

            entities = await exa.beta.agent.monitors.entities.get_all("agentmon_123", betas=[AGENT_MONITORS_BETA_HEADER])
            print(len(entities))
        """
        return [
            entity_view
            async for entity_view in self.list_all(
                monitor_id, betas=betas, cursor=cursor, limit=limit, since=since
            )
        ]


class AsyncAgentMonitorChangesClient(AsyncAgentMonitorsBaseClient):
    """Asynchronous client for an Agent Monitor's content change feed."""

    async def list(
        self,
        monitor_id: str,
        *,
        betas: Sequence[str],
        cursor: Optional[str] = None,
        limit: Optional[int] = None,
        since: Optional[str] = None,
    ) -> ListAgentMonitorChangesResponse:
        """Page an Agent Monitor's content change feed since a cursor or timestamp.

        Args:
            betas: Beta feature identifiers to enable for this request.
            monitor_id: The ID of the Agent Monitor.
            cursor: Pagination cursor from a previous response; resumes the
                feed from the last served change.
            limit: Maximum number of changes to return.
            since: Only return changes committed at or after this ISO-8601
                timestamp.

        Returns:
            One page of content changes.

        Examples:
            from exa_py import AsyncExa
            from exa_py.agent import AGENT_MONITORS_BETA_HEADER

            exa = AsyncExa("EXA_API_KEY")

            changes = await exa.beta.agent.monitors.changes.list(
                "agentmon_123",
                betas=[AGENT_MONITORS_BETA_HEADER],
                since="2026-01-01T00:00:00Z",
            )
            for change in changes.data:
                print(change.entity.name, change.field.name, change.content.value)
        """
        params = self.build_pagination_params(cursor, limit, since)
        response = await self.request(
            f"/{monitor_id}/changes", betas=betas, method="GET", params=params
        )
        return ListAgentMonitorChangesResponse.model_validate(response)

    async def list_all(
        self,
        monitor_id: str,
        *,
        betas: Sequence[str],
        cursor: Optional[str] = None,
        limit: Optional[int] = None,
        since: Optional[str] = None,
    ) -> AsyncIterator[AgentMonitorChange]:
        """Iterate through a monitor's change feed, handling pagination automatically.

        Args:
            betas: Beta feature identifiers to enable for this request.
            monitor_id: The ID of the Agent Monitor.
            cursor: Change-feed cursor to resume from.
            limit: Maximum number of changes to return per page.
            since: Only return changes committed at or after this ISO-8601
                timestamp.

        Yields:
            AgentMonitorChange: Each content change.

        Examples:
            from exa_py import AsyncExa
            from exa_py.agent import AGENT_MONITORS_BETA_HEADER

            exa = AsyncExa("EXA_API_KEY")

            async for change in exa.beta.agent.monitors.changes.list_all("agentmon_123", betas=[AGENT_MONITORS_BETA_HEADER]):
                print(change.created_at, change.content.value)
        """
        while True:
            response = await self.list(
                monitor_id,
                betas=betas,
                cursor=cursor,
                limit=limit,
                since=since,
            )
            for change in response.data:
                yield change
            if not response.has_more or not response.next_cursor:
                break
            cursor = response.next_cursor

    async def get_all(
        self,
        monitor_id: str,
        *,
        betas: Sequence[str],
        cursor: Optional[str] = None,
        limit: Optional[int] = None,
        since: Optional[str] = None,
    ) -> list[AgentMonitorChange]:
        """Collect a monitor's change feed into a list.

        Args:
            betas: Beta feature identifiers to enable for this request.
            monitor_id: The ID of the Agent Monitor.
            cursor: Change-feed cursor to resume from.
            limit: Maximum number of changes to return per page.
            since: Only return changes committed at or after this ISO-8601
                timestamp.

        Returns:
            List of content changes.

        Examples:
            from exa_py import AsyncExa
            from exa_py.agent import AGENT_MONITORS_BETA_HEADER

            exa = AsyncExa("EXA_API_KEY")

            changes = await exa.beta.agent.monitors.changes.get_all("agentmon_123", betas=[AGENT_MONITORS_BETA_HEADER])
            print(len(changes))
        """
        return [
            change
            async for change in self.list_all(
                monitor_id,
                betas=betas,
                cursor=cursor,
                limit=limit,
                since=since,
            )
        ]


class AsyncAgentMonitorBacktestsClient(AsyncAgentMonitorsBaseClient):
    """Asynchronous client for one-shot Agent Monitor backtest jobs."""

    async def create(
        self,
        *,
        betas: Sequence[str],
        entities: Sequence[EntityInput],
        fields: Sequence[FieldInput],
        start_time: str,
        end_time: str,
    ) -> AgentMonitorBacktest:
        """Start an async backtest of entities x fields over a past news window.

        The backtest runs one ordinary monitor refresh over the requested
        window, then tears down its temporary monitor.

        Args:
            betas: Beta feature identifiers to enable for this request.
            entities: Entities to backtest, each with a name and a unique domain.
            fields: Fields to populate from news over the window.
            start_time: Start of the news window as an ISO-8601 UTC timestamp.
            end_time: End of the news window as an ISO-8601 UTC timestamp.

        Returns:
            The running backtest job; poll it with `get` or use `create_and_wait`.

        Examples:
            from exa_py import AsyncExa
            from exa_py.agent import AGENT_MONITORS_BETA_HEADER

            exa = AsyncExa("EXA_API_KEY")

            backtest = await exa.beta.agent.monitors.backtests.create(
                betas=[AGENT_MONITORS_BETA_HEADER],
                entities=[{"name": "Acme Corp", "domain": "acme.com"}],
                fields=[
                    {
                        "name": "funding",
                        "description": "New funding rounds",
                    }
                ],
                start_time="2026-01-01T00:00:00Z",
                end_time="2026-01-08T00:00:00Z",
            )
            print(backtest.id, backtest.status)
        """
        payload: Dict[str, Any] = {
            "entities": _serialize_entities(entities),
            "fields": _serialize_fields(fields),
            "startTime": start_time,
            "endTime": end_time,
        }
        response = await self.request(
            "/backtest", betas=betas, method="POST", data=payload
        )
        return AgentMonitorBacktest.model_validate(response)

    async def get(
        self, backtest_id: str, *, betas: Sequence[str]
    ) -> AgentMonitorBacktest:
        """Poll a backtest job for its status and, once completed, its result.

        Jobs expire and read as 404 after `expires_at`.

        Args:
            betas: Beta feature identifiers to enable for this request.
            backtest_id: The ID of the backtest job.

        Returns:
            The backtest job, with result data once completed.

        Examples:
            from exa_py import AsyncExa
            from exa_py.agent import AGENT_MONITORS_BETA_HEADER

            exa = AsyncExa("EXA_API_KEY")

            backtest = await exa.beta.agent.monitors.backtests.get("agentbacktest_123", betas=[AGENT_MONITORS_BETA_HEADER])
            print(backtest.status)
        """
        response = await self.request(
            f"/backtest/{backtest_id}", betas=betas, method="GET"
        )
        return AgentMonitorBacktest.model_validate(response)

    async def poll_until_finished(
        self,
        backtest_id: str,
        *,
        betas: Sequence[str],
        poll_interval: int = _DEFAULT_BACKTEST_POLL_INTERVAL_MS,
        timeout_ms: int = _DEFAULT_BACKTEST_POLL_TIMEOUT_MS,
    ) -> AgentMonitorBacktest:
        """Poll a backtest job until it reaches a terminal status.

        Args:
            betas: Beta feature identifiers to enable for this request.
            backtest_id: The ID of the backtest job.
            poll_interval: Delay between polls in milliseconds.
            timeout_ms: Maximum time to wait in milliseconds.

        Returns:
            The terminal backtest job (completed or failed).

        Examples:
            from exa_py import AsyncExa
            from exa_py.agent import AGENT_MONITORS_BETA_HEADER

            exa = AsyncExa("EXA_API_KEY")

            backtest = await exa.beta.agent.monitors.backtests.poll_until_finished(
                "agentbacktest_123", betas=[AGENT_MONITORS_BETA_HEADER]
            )
            print(backtest.status)
        """
        start_time = time.monotonic()
        poll_interval_sec = poll_interval / 1000

        while True:
            backtest = await self.get(backtest_id, betas=betas)
            if backtest.status != "running":
                return backtest

            if (time.monotonic() - start_time) * 1000 > timeout_ms:
                raise TimeoutError(
                    f"Agent monitor backtest {backtest_id} did not complete within {timeout_ms}ms"
                )

            await asyncio.sleep(poll_interval_sec)

    async def create_and_wait(
        self,
        *,
        betas: Sequence[str],
        entities: Sequence[EntityInput],
        fields: Sequence[FieldInput],
        start_time: str,
        end_time: str,
        poll_interval: int = _DEFAULT_BACKTEST_POLL_INTERVAL_MS,
        timeout_ms: int = _DEFAULT_BACKTEST_POLL_TIMEOUT_MS,
    ) -> AgentMonitorBacktest:
        """Start a backtest and wait for its result.

        Args:
            betas: Beta feature identifiers to enable for this request.
            entities: Entities to backtest, each with a name and a unique domain.
            fields: Fields to populate from news over the window.
            start_time: Start of the news window as an ISO-8601 UTC timestamp.
            end_time: End of the news window as an ISO-8601 UTC timestamp.
            poll_interval: Delay between polls in milliseconds.
            timeout_ms: Maximum time to wait in milliseconds.

        Returns:
            The completed backtest job.

        Raises:
            AgentMonitorBacktestFailedError: If the backtest job fails.

        Examples:
            from exa_py import AsyncExa
            from exa_py.agent import AGENT_MONITORS_BETA_HEADER

            exa = AsyncExa("EXA_API_KEY")

            backtest = await exa.beta.agent.monitors.backtests.create_and_wait(
                betas=[AGENT_MONITORS_BETA_HEADER],
                entities=[{"name": "Acme Corp", "domain": "acme.com"}],
                fields=[
                    {
                        "name": "funding",
                        "description": "New funding rounds",
                    }
                ],
                start_time="2026-01-01T00:00:00Z",
                end_time="2026-01-08T00:00:00Z",
            )
            print(backtest.data)
        """
        backtest = await self.create(
            betas=betas,
            entities=entities,
            fields=fields,
            start_time=start_time,
            end_time=end_time,
        )
        if backtest.status == "running":
            backtest = await self.poll_until_finished(
                backtest.id,
                betas=betas,
                poll_interval=poll_interval,
                timeout_ms=timeout_ms,
            )
        return _ensure_completed_backtest(backtest)


class AsyncAgentMonitorsClient(AsyncAgentMonitorsBaseClient):
    """Asynchronous client for Agent Monitors."""

    entities: AsyncAgentMonitorEntitiesClient
    changes: AsyncAgentMonitorChangesClient
    backtests: AsyncAgentMonitorBacktestsClient

    def __init__(self, client: Any):
        super().__init__(client)
        self.entities = AsyncAgentMonitorEntitiesClient(client)
        self.changes = AsyncAgentMonitorChangesClient(client)
        self.backtests = AsyncAgentMonitorBacktestsClient(client)

    async def create(
        self,
        *,
        betas: Sequence[str],
        cadence: str,
        entities: Sequence[EntityInput],
        fields: Sequence[FieldInput],
        idempotency_key: Optional[str] = None,
    ) -> AgentMonitor:
        """Create an Agent Monitor from its entities, fields, and cadence.

        Creation is async: the monitor is returned with status `creating` and
        becomes `active` once its first refresh completes.

        Args:
            betas: Beta feature identifiers to enable for this request.
            cadence: How often the monitor refreshes, e.g. `"12h"` or `"7d"`
                (minimum 6h). Also each refresh's news lookback window.
            entities: Entities to track, each with a name and a unique domain.
            fields: Fields to keep fresh; dynamic by default (tracked from news
                on every refresh), `mode: "static"` fields are answered once
                over the live web.
            idempotency_key: Sent as the `Idempotency-Key` header. A retried
                create with the same key returns the monitor the first attempt
                created instead of creating a duplicate.

        Returns:
            The created Agent Monitor.

        Examples:
            from exa_py import AsyncExa
            from exa_py.agent import AGENT_MONITORS_BETA_HEADER

            exa = AsyncExa("EXA_API_KEY")

            monitor = await exa.beta.agent.monitors.create(
                betas=[AGENT_MONITORS_BETA_HEADER],
                cadence="7d",
                entities=[{"name": "Acme Corp", "domain": "acme.com"}],
                fields=[
                    {"name": "ceo", "description": "The company's current CEO"},
                    {
                        "name": "funding",
                        "description": "New funding rounds",
                        "mode": "dynamic",
                    },
                ],
            )
            print(monitor.id, monitor.status)
        """
        payload = {
            "cadence": cadence,
            "entities": _serialize_entities(entities),
            "fields": _serialize_fields(fields),
        }
        headers = (
            {"Idempotency-Key": idempotency_key}
            if idempotency_key is not None
            else None
        )
        response = await self.request(
            "", betas=betas, method="POST", data=payload, headers=headers
        )
        return AgentMonitor.model_validate(response)

    async def get(self, monitor_id: str, *, betas: Sequence[str]) -> AgentMonitor:
        """Get an Agent Monitor by ID, including refresh progress.

        Args:
            betas: Beta feature identifiers to enable for this request.
            monitor_id: The ID of the Agent Monitor.

        Returns:
            The Agent Monitor.

        Examples:
            from exa_py import AsyncExa
            from exa_py.agent import AGENT_MONITORS_BETA_HEADER

            exa = AsyncExa("EXA_API_KEY")

            monitor = await exa.beta.agent.monitors.get("agentmon_123", betas=[AGENT_MONITORS_BETA_HEADER])
            print(monitor.status, monitor.refresh)
        """
        response = await self.request(f"/{monitor_id}", betas=betas, method="GET")
        return AgentMonitor.model_validate(response)

    async def list(
        self,
        *,
        betas: Sequence[str],
        cursor: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> ListAgentMonitorsResponse:
        """List the team's Agent Monitors.

        Args:
            betas: Beta feature identifiers to enable for this request.
            cursor: Pagination cursor from a previous response.
            limit: Maximum number of monitors to return.

        Returns:
            List of Agent Monitors with pagination info.

        Examples:
            from exa_py import AsyncExa
            from exa_py.agent import AGENT_MONITORS_BETA_HEADER

            exa = AsyncExa("EXA_API_KEY")

            monitors = await exa.beta.agent.monitors.list(betas=[AGENT_MONITORS_BETA_HEADER], limit=10)
            print([monitor.id for monitor in monitors.data])
        """
        params = self.build_pagination_params(cursor, limit)
        response = await self.request("", betas=betas, method="GET", params=params)
        return ListAgentMonitorsResponse.model_validate(response)

    async def list_all(
        self,
        *,
        betas: Sequence[str],
        cursor: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> AsyncIterator[AgentMonitor]:
        """Iterate through all Agent Monitors, handling pagination automatically.

        Args:
            betas: Beta feature identifiers to enable for this request.
            cursor: Monitors list cursor to resume from.
            limit: Maximum number of monitors to return per page.

        Yields:
            AgentMonitor: Each Agent Monitor.

        Examples:
            from exa_py import AsyncExa
            from exa_py.agent import AGENT_MONITORS_BETA_HEADER

            exa = AsyncExa("EXA_API_KEY")

            async for monitor in exa.beta.agent.monitors.list_all(betas=[AGENT_MONITORS_BETA_HEADER]):
                print(monitor.id)
        """
        while True:
            response = await self.list(betas=betas, cursor=cursor, limit=limit)
            for monitor in response.data:
                yield monitor
            if not response.has_more or not response.next_cursor:
                break
            cursor = response.next_cursor

    async def get_all(
        self,
        *,
        betas: Sequence[str],
        cursor: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> list[AgentMonitor]:
        """Collect all Agent Monitors into a list.

        Args:
            betas: Beta feature identifiers to enable for this request.
            cursor: Monitors list cursor to resume from.
            limit: Maximum number of monitors to return per page.

        Returns:
            List of all Agent Monitors.

        Examples:
            from exa_py import AsyncExa
            from exa_py.agent import AGENT_MONITORS_BETA_HEADER

            exa = AsyncExa("EXA_API_KEY")

            monitors = await exa.beta.agent.monitors.get_all(betas=[AGENT_MONITORS_BETA_HEADER])
            print(len(monitors))
        """
        return [
            monitor
            async for monitor in self.list_all(betas=betas, cursor=cursor, limit=limit)
        ]

    async def delete(
        self, monitor_id: str, *, betas: Sequence[str]
    ) -> DeletedAgentMonitor:
        """Delete an Agent Monitor and stop its refreshes.

        Args:
            betas: Beta feature identifiers to enable for this request.
            monitor_id: The ID of the Agent Monitor.

        Returns:
            Deletion status for the Agent Monitor.

        Examples:
            from exa_py import AsyncExa
            from exa_py.agent import AGENT_MONITORS_BETA_HEADER

            exa = AsyncExa("EXA_API_KEY")

            deleted = await exa.beta.agent.monitors.delete("agentmon_123", betas=[AGENT_MONITORS_BETA_HEADER])
            print(deleted.deleted)
        """
        response = await self.request(f"/{monitor_id}", betas=betas, method="DELETE")
        return DeletedAgentMonitor.model_validate(response)
