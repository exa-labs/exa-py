"""Synchronous Exa Agent Monitors API client."""

from __future__ import annotations

import time
from typing import Any, Dict, Iterator, Optional, Sequence, Union

from .base import AgentMonitorsBaseClient
from .types import (
    AgentMonitor,
    AgentMonitorChange,
    AgentMonitorEntityParam,
    AgentMonitorEntityView,
    AgentMonitorFieldParam,
    AgentMonitorSnapshot,
    AgentMonitorSnapshotFailedError,
    DeletedAgentMonitor,
    ListAgentMonitorChangesResponse,
    ListAgentMonitorEntitiesResponse,
    ListAgentMonitorsResponse,
)

_DEFAULT_SNAPSHOT_POLL_INTERVAL_MS = 2000
_DEFAULT_SNAPSHOT_POLL_TIMEOUT_MS = 3600000

EntityInput = Union[Dict[str, Any], AgentMonitorEntityParam]
FieldInput = Union[Dict[str, Any], AgentMonitorFieldParam]


def _serialize_entities(entities: Sequence[EntityInput]) -> list[Dict[str, Any]]:
    return [
        AgentMonitorEntityParam.model_validate(entity).model_dump(
            by_alias=True, exclude_none=True
        )
        for entity in entities
    ]


def _serialize_fields(fields: Sequence[FieldInput]) -> list[Dict[str, Any]]:
    return [
        AgentMonitorFieldParam.model_validate(field).model_dump(
            by_alias=True, exclude_none=True
        )
        for field in fields
    ]


def _ensure_completed_snapshot(snapshot: AgentMonitorSnapshot) -> AgentMonitorSnapshot:
    if snapshot.status == "failed":
        raise AgentMonitorSnapshotFailedError(snapshot)
    return snapshot


class AgentMonitorEntitiesClient(AgentMonitorsBaseClient):
    """Synchronous client for an Agent Monitor's entities."""

    def add(
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
            from exa_py import Exa
            from exa_py.agent import AGENT_MONITORS_BETA_HEADER

            exa = Exa("EXA_API_KEY")

            monitor = exa.beta.agent.monitors.entities.add(
                "agentmon_123",
                betas=[AGENT_MONITORS_BETA_HEADER],
                entities=[{"name": "Initech", "domain": "initech.com"}],
            )
            print(monitor.entity_count)
        """
        payload = {"entities": _serialize_entities(entities)}
        response = self.request(
            f"/{monitor_id}/entities", betas=betas, method="POST", data=payload
        )
        return AgentMonitor.model_validate(response)

    def list(
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
            from exa_py import Exa
            from exa_py.agent import AGENT_MONITORS_BETA_HEADER

            exa = Exa("EXA_API_KEY")

            page = exa.beta.agent.monitors.entities.list("agentmon_123", betas=[AGENT_MONITORS_BETA_HEADER], limit=50)
            for view in page.data:
                print(view.entity.name, view.contents)
        """
        params = self.build_pagination_params(cursor, limit, since)
        response = self.request(
            f"/{monitor_id}/entities", betas=betas, method="GET", params=params
        )
        return ListAgentMonitorEntitiesResponse.model_validate(response)

    def list_all(
        self,
        monitor_id: str,
        *,
        betas: Sequence[str],
        cursor: Optional[str] = None,
        limit: Optional[int] = None,
        since: Optional[str] = None,
    ) -> Iterator[AgentMonitorEntityView]:
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
            from exa_py import Exa
            from exa_py.agent import AGENT_MONITORS_BETA_HEADER

            exa = Exa("EXA_API_KEY")

            for view in exa.beta.agent.monitors.entities.list_all("agentmon_123", betas=[AGENT_MONITORS_BETA_HEADER]):
                print(view.entity.name)
        """
        while True:
            response = self.list(
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

    def get_all(
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
            from exa_py import Exa
            from exa_py.agent import AGENT_MONITORS_BETA_HEADER

            exa = Exa("EXA_API_KEY")

            entities = exa.beta.agent.monitors.entities.get_all("agentmon_123", betas=[AGENT_MONITORS_BETA_HEADER])
            print(len(entities))
        """
        return list(
            self.list_all(
                monitor_id, betas=betas, cursor=cursor, limit=limit, since=since
            )
        )


class AgentMonitorChangesClient(AgentMonitorsBaseClient):
    """Synchronous client for an Agent Monitor's content change feed."""

    def list(
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
            from exa_py import Exa
            from exa_py.agent import AGENT_MONITORS_BETA_HEADER

            exa = Exa("EXA_API_KEY")

            changes = exa.beta.agent.monitors.changes.list(
                "agentmon_123",
                betas=[AGENT_MONITORS_BETA_HEADER],
                since="2026-01-01T00:00:00Z",
            )
            for change in changes.data:
                print(change.entity.name, change.field.name, change.content.value)
        """
        params = self.build_pagination_params(cursor, limit, since)
        response = self.request(
            f"/{monitor_id}/changes", betas=betas, method="GET", params=params
        )
        return ListAgentMonitorChangesResponse.model_validate(response)

    def list_all(
        self,
        monitor_id: str,
        *,
        betas: Sequence[str],
        cursor: Optional[str] = None,
        limit: Optional[int] = None,
        since: Optional[str] = None,
    ) -> Iterator[AgentMonitorChange]:
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
            from exa_py import Exa
            from exa_py.agent import AGENT_MONITORS_BETA_HEADER

            exa = Exa("EXA_API_KEY")

            for change in exa.beta.agent.monitors.changes.list_all("agentmon_123", betas=[AGENT_MONITORS_BETA_HEADER]):
                print(change.created_at, change.content.value)
        """
        while True:
            response = self.list(
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

    def get_all(
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
            from exa_py import Exa
            from exa_py.agent import AGENT_MONITORS_BETA_HEADER

            exa = Exa("EXA_API_KEY")

            changes = exa.beta.agent.monitors.changes.get_all("agentmon_123", betas=[AGENT_MONITORS_BETA_HEADER])
            print(len(changes))
        """
        return list(
            self.list_all(
                monitor_id,
                betas=betas,
                cursor=cursor,
                limit=limit,
                since=since,
            )
        )


class AgentMonitorSnapshotsClient(AgentMonitorsBaseClient):
    """Synchronous client for stateless Agent Monitor snapshot jobs."""

    def create(
        self,
        *,
        betas: Sequence[str],
        entities: Sequence[EntityInput],
        fields: Sequence[FieldInput],
        start_date: str,
        end_date: str,
        start_hour: Optional[int] = None,
        end_hour: Optional[int] = None,
    ) -> AgentMonitorSnapshot:
        """Start an async, stateless snapshot of entities x fields over a past news window.

        No monitor is created. The window bounds dynamic fields only; static
        fields return present values answered over the live web, and the
        result carries a warning when static fields are included.

        Args:
            betas: Beta feature identifiers to enable for this request.
            entities: Entities to snapshot, each with a name and a unique domain.
            fields: Fields to populate; dynamic by default (populated from news
                over the window), `mode: "static"` fields are answered over the
                live web.
            start_date: Start of the news window, `YYYY-MM-DD` (UTC).
            end_date: End of the news window, `YYYY-MM-DD` (UTC).
            start_hour: Hour of start_date the window starts at, 0-23 UTC;
                omitted means midnight.
            end_hour: Hour of end_date the window ends at, 0-23 UTC; omitted
                means midnight.

        Returns:
            The running snapshot job; poll it with `get` or use `create_and_wait`.

        Examples:
            from exa_py import Exa
            from exa_py.agent import AGENT_MONITORS_BETA_HEADER

            exa = Exa("EXA_API_KEY")

            snapshot = exa.beta.agent.monitors.snapshots.create(
                betas=[AGENT_MONITORS_BETA_HEADER],
                entities=[{"name": "Acme Corp", "domain": "acme.com"}],
                fields=[
                    {
                        "name": "funding",
                        "description": "New funding rounds",
                        "mode": "dynamic",
                    }
                ],
                start_date="2026-01-01",
                end_date="2026-01-08",
            )
            print(snapshot.id, snapshot.status)
        """
        payload: Dict[str, Any] = {
            "entities": _serialize_entities(entities),
            "fields": _serialize_fields(fields),
            "startDate": start_date,
            "endDate": end_date,
        }
        if start_hour is not None:
            payload["startHour"] = start_hour
        if end_hour is not None:
            payload["endHour"] = end_hour
        response = self.request("/snapshot", betas=betas, method="POST", data=payload)
        return AgentMonitorSnapshot.model_validate(response)

    def get(self, snapshot_id: str, *, betas: Sequence[str]) -> AgentMonitorSnapshot:
        """Poll a snapshot job for its status and, once completed, its result.

        Jobs expire and read as 404 after `expires_at`.

        Args:
            betas: Beta feature identifiers to enable for this request.
            snapshot_id: The ID of the snapshot job.

        Returns:
            The snapshot job, with result data once completed.

        Examples:
            from exa_py import Exa
            from exa_py.agent import AGENT_MONITORS_BETA_HEADER

            exa = Exa("EXA_API_KEY")

            snapshot = exa.beta.agent.monitors.snapshots.get("agentsnap_123", betas=[AGENT_MONITORS_BETA_HEADER])
            print(snapshot.status)
        """
        response = self.request(f"/snapshot/{snapshot_id}", betas=betas, method="GET")
        return AgentMonitorSnapshot.model_validate(response)

    def poll_until_finished(
        self,
        snapshot_id: str,
        *,
        betas: Sequence[str],
        poll_interval: int = _DEFAULT_SNAPSHOT_POLL_INTERVAL_MS,
        timeout_ms: int = _DEFAULT_SNAPSHOT_POLL_TIMEOUT_MS,
    ) -> AgentMonitorSnapshot:
        """Poll a snapshot job until it reaches a terminal status.

        Args:
            betas: Beta feature identifiers to enable for this request.
            snapshot_id: The ID of the snapshot job.
            poll_interval: Delay between polls in milliseconds.
            timeout_ms: Maximum time to wait in milliseconds.

        Returns:
            The terminal snapshot job (completed or failed).

        Examples:
            from exa_py import Exa
            from exa_py.agent import AGENT_MONITORS_BETA_HEADER

            exa = Exa("EXA_API_KEY")

            snapshot = exa.beta.agent.monitors.snapshots.poll_until_finished("agentsnap_123", betas=[AGENT_MONITORS_BETA_HEADER])
            print(snapshot.status)
        """
        start_time = time.monotonic()
        poll_interval_sec = poll_interval / 1000

        while True:
            snapshot = self.get(snapshot_id, betas=betas)
            if snapshot.status != "running":
                return snapshot

            if (time.monotonic() - start_time) * 1000 > timeout_ms:
                raise TimeoutError(
                    f"Agent monitor snapshot {snapshot_id} did not complete within {timeout_ms}ms"
                )

            time.sleep(poll_interval_sec)

    def create_and_wait(
        self,
        *,
        betas: Sequence[str],
        entities: Sequence[EntityInput],
        fields: Sequence[FieldInput],
        start_date: str,
        end_date: str,
        start_hour: Optional[int] = None,
        end_hour: Optional[int] = None,
        poll_interval: int = _DEFAULT_SNAPSHOT_POLL_INTERVAL_MS,
        timeout_ms: int = _DEFAULT_SNAPSHOT_POLL_TIMEOUT_MS,
    ) -> AgentMonitorSnapshot:
        """Start a snapshot and wait for its result.

        Args:
            betas: Beta feature identifiers to enable for this request.
            entities: Entities to snapshot, each with a name and a unique domain.
            fields: Fields to populate; dynamic by default (populated from news
                over the window), `mode: "static"` fields are answered over the
                live web.
            start_date: Start of the news window, `YYYY-MM-DD` (UTC).
            end_date: End of the news window, `YYYY-MM-DD` (UTC).
            start_hour: Hour of start_date the window starts at, 0-23 UTC;
                omitted means midnight.
            end_hour: Hour of end_date the window ends at, 0-23 UTC; omitted
                means midnight.
            poll_interval: Delay between polls in milliseconds.
            timeout_ms: Maximum time to wait in milliseconds.

        Returns:
            The completed snapshot job.

        Raises:
            AgentMonitorSnapshotFailedError: If the snapshot job fails.

        Examples:
            from exa_py import Exa
            from exa_py.agent import AGENT_MONITORS_BETA_HEADER

            exa = Exa("EXA_API_KEY")

            snapshot = exa.beta.agent.monitors.snapshots.create_and_wait(
                betas=[AGENT_MONITORS_BETA_HEADER],
                entities=[{"name": "Acme Corp", "domain": "acme.com"}],
                fields=[
                    {
                        "name": "funding",
                        "description": "New funding rounds",
                        "mode": "dynamic",
                    }
                ],
                start_date="2026-01-01",
                end_date="2026-01-08",
            )
            print(snapshot.data)
        """
        snapshot = self.create(
            betas=betas,
            entities=entities,
            fields=fields,
            start_date=start_date,
            end_date=end_date,
            start_hour=start_hour,
            end_hour=end_hour,
        )
        if snapshot.status == "running":
            snapshot = self.poll_until_finished(
                snapshot.id,
                betas=betas,
                poll_interval=poll_interval,
                timeout_ms=timeout_ms,
            )
        return _ensure_completed_snapshot(snapshot)


class AgentMonitorsClient(AgentMonitorsBaseClient):
    """Synchronous client for Agent Monitors."""

    entities: AgentMonitorEntitiesClient
    changes: AgentMonitorChangesClient
    snapshots: AgentMonitorSnapshotsClient

    def __init__(self, client: Any):
        super().__init__(client)
        self.entities = AgentMonitorEntitiesClient(client)
        self.changes = AgentMonitorChangesClient(client)
        self.snapshots = AgentMonitorSnapshotsClient(client)

    def create(
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
            from exa_py import Exa
            from exa_py.agent import AGENT_MONITORS_BETA_HEADER

            exa = Exa("EXA_API_KEY")

            monitor = exa.beta.agent.monitors.create(
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
        response = self.request(
            "", betas=betas, method="POST", data=payload, headers=headers
        )
        return AgentMonitor.model_validate(response)

    def get(self, monitor_id: str, *, betas: Sequence[str]) -> AgentMonitor:
        """Get an Agent Monitor by ID, including refresh progress.

        Args:
            betas: Beta feature identifiers to enable for this request.
            monitor_id: The ID of the Agent Monitor.

        Returns:
            The Agent Monitor.

        Examples:
            from exa_py import Exa
            from exa_py.agent import AGENT_MONITORS_BETA_HEADER

            exa = Exa("EXA_API_KEY")

            monitor = exa.beta.agent.monitors.get("agentmon_123", betas=[AGENT_MONITORS_BETA_HEADER])
            print(monitor.status, monitor.refresh)
        """
        response = self.request(f"/{monitor_id}", betas=betas, method="GET")
        return AgentMonitor.model_validate(response)

    def list(
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
            from exa_py import Exa
            from exa_py.agent import AGENT_MONITORS_BETA_HEADER

            exa = Exa("EXA_API_KEY")

            monitors = exa.beta.agent.monitors.list(betas=[AGENT_MONITORS_BETA_HEADER], limit=10)
            print([monitor.id for monitor in monitors.data])
        """
        params = self.build_pagination_params(cursor, limit)
        response = self.request("", betas=betas, method="GET", params=params)
        return ListAgentMonitorsResponse.model_validate(response)

    def list_all(
        self,
        *,
        betas: Sequence[str],
        cursor: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Iterator[AgentMonitor]:
        """Iterate through all Agent Monitors, handling pagination automatically.

        Args:
            betas: Beta feature identifiers to enable for this request.
            cursor: Monitors list cursor to resume from.
            limit: Maximum number of monitors to return per page.

        Yields:
            AgentMonitor: Each Agent Monitor.

        Examples:
            from exa_py import Exa
            from exa_py.agent import AGENT_MONITORS_BETA_HEADER

            exa = Exa("EXA_API_KEY")

            for monitor in exa.beta.agent.monitors.list_all(betas=[AGENT_MONITORS_BETA_HEADER]):
                print(monitor.id)
        """
        while True:
            response = self.list(betas=betas, cursor=cursor, limit=limit)
            for monitor in response.data:
                yield monitor
            if not response.has_more or not response.next_cursor:
                break
            cursor = response.next_cursor

    def get_all(
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
            from exa_py import Exa
            from exa_py.agent import AGENT_MONITORS_BETA_HEADER

            exa = Exa("EXA_API_KEY")

            monitors = exa.beta.agent.monitors.get_all(betas=[AGENT_MONITORS_BETA_HEADER])
            print(len(monitors))
        """
        return list(self.list_all(betas=betas, cursor=cursor, limit=limit))

    def delete(self, monitor_id: str, *, betas: Sequence[str]) -> DeletedAgentMonitor:
        """Delete an Agent Monitor and stop its refreshes.

        Args:
            betas: Beta feature identifiers to enable for this request.
            monitor_id: The ID of the Agent Monitor.

        Returns:
            Deletion status for the Agent Monitor.

        Examples:
            from exa_py import Exa
            from exa_py.agent import AGENT_MONITORS_BETA_HEADER

            exa = Exa("EXA_API_KEY")

            deleted = exa.beta.agent.monitors.delete("agentmon_123", betas=[AGENT_MONITORS_BETA_HEADER])
            print(deleted.deleted)
        """
        response = self.request(f"/{monitor_id}", betas=betas, method="DELETE")
        return DeletedAgentMonitor.model_validate(response)
