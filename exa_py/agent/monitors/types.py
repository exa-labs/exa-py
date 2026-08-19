"""Types for the Exa Agent Monitors API (`/agent/monitors`).

An Agent Monitor keeps a table of entities x fields fresh: static fields are
answered once per entity over the live web, dynamic fields are tracked from
news on every refresh, on the monitor's cadence.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, model_validator


AGENT_MONITORS_BETA_HEADER = "agent-monitors-2026-08-04"

AgentMonitorStatus = Literal["creating", "pending_first_refresh", "active"]
AgentMonitorFieldMode = Literal["static", "dynamic"]
"""How a field is kept fresh: dynamic (every refresh) or static (answered once)."""
AgentMonitorFieldValueType = Literal[
    "string", "number", "boolean", "date", "url", "email", "phone"
]
"""The type of a field's cell values."""
AgentMonitorFieldType = AgentMonitorFieldMode
"""Deprecated: renamed to `AgentMonitorFieldMode`."""
AgentMonitorSnapshotStatus = Literal["running", "completed", "failed"]


class AgentMonitorField(BaseModel):
    """A field the monitor keeps fresh for every entity.

    Fields are dynamic (tracked from news on every refresh) unless declared
    `mode: "static"` (answered once over the live web).
    """

    id: str
    name: str
    description: str
    mode: AgentMonitorFieldMode = "dynamic"
    """Deprecated: the static/dynamic knob is becoming internal-only."""
    type: Union[AgentMonitorFieldValueType, str] = "string"
    """The type of the field's cell values."""

    @model_validator(mode="before")
    @classmethod
    def _fill_mode_from_legacy_type(cls, data: Any) -> Any:
        if (
            isinstance(data, dict)
            and "mode" not in data
            and data.get("type") in ("static", "dynamic")
        ):
            data = {**data, "mode": data["type"]}
        return data

    model_config = {"populate_by_name": True, "extra": "allow"}


class AgentMonitorEntity(BaseModel):
    """An entity tracked by the monitor."""

    id: str
    name: str
    domain: Optional[str] = None
    canonical_entity_id: Optional[str] = Field(default=None, alias="canonicalEntityId")

    model_config = {"populate_by_name": True, "extra": "allow"}


class AgentMonitorCitation(BaseModel):
    """One grounding citation for a cell value; the Agent API's citation shape."""

    url: str
    title: Optional[str] = None
    note: Optional[str] = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class AgentMonitorContent(BaseModel):
    """One cell value: a field's current content for an entity."""

    value: Optional[Any] = None
    citations: Optional[List[AgentMonitorCitation]] = None
    """Grounding for the value, in the Agent API's citation shape."""
    updated_at: str = Field(alias="updatedAt")

    model_config = {"populate_by_name": True, "extra": "allow"}


class AgentMonitorRefresh(BaseModel):
    """Refresh progress on the monitor object; `idle` outside an active refresh."""

    state: Literal["idle", "running"]
    entities_processed: Optional[int] = Field(default=None, alias="entitiesProcessed")
    entities_total: Optional[int] = Field(default=None, alias="entitiesTotal")
    started_at: Optional[str] = Field(default=None, alias="startedAt")

    model_config = {"populate_by_name": True, "extra": "allow"}


class AgentMonitorCreation(BaseModel):
    """Creation progress on the monitor object; `idle` once the monitor is set up."""

    state: Literal["idle", "running"]
    entities_processed: Optional[int] = Field(default=None, alias="entitiesProcessed")
    entities_total: Optional[int] = Field(default=None, alias="entitiesTotal")
    started_at: Optional[str] = Field(default=None, alias="startedAt")

    model_config = {"populate_by_name": True, "extra": "allow"}


class AgentMonitorUsage(BaseModel):
    """ACU consumption on the monitor object; ACUs are the unit Agent runs bill in."""

    total_acus: float = Field(alias="totalAcus")
    last_refresh_acus: float = Field(alias="lastRefreshAcus")

    model_config = {"populate_by_name": True, "extra": "allow"}


class AgentMonitor(BaseModel):
    id: str
    object: Optional[str] = None
    status: AgentMonitorStatus
    cadence: str
    """Refresh cadence, e.g. `"12h"` or `"7d"`; also each refresh's lookback window."""
    fields: List[AgentMonitorField]
    entity_count: int = Field(alias="entityCount")
    version: int
    created_at: str = Field(alias="createdAt")
    last_refresh_at: Optional[str] = Field(default=None, alias="lastRefreshAt")
    refresh: Optional[AgentMonitorRefresh] = None
    creation: Optional[AgentMonitorCreation] = None
    usage: Optional[AgentMonitorUsage] = None
    source_run_id: Optional[str] = Field(default=None, alias="sourceRunId")

    model_config = {"populate_by_name": True, "extra": "allow"}


class AgentMonitorEntityView(BaseModel):
    """One entity and its current contents, keyed by field id."""

    entity: AgentMonitorEntity
    contents: Dict[str, AgentMonitorContent]

    model_config = {"populate_by_name": True, "extra": "allow"}


class AgentMonitorChangeEntity(BaseModel):
    """Entity reference on a change item.

    `id` is the canonical, stable join key; the name attributes are
    denormalized for display, resolved as of read time, and absent when the
    entity no longer exists.
    """

    id: str
    name: Optional[str] = None
    domain: Optional[str] = None
    canonical_entity_id: Optional[str] = Field(default=None, alias="canonicalEntityId")

    model_config = {"populate_by_name": True, "extra": "allow"}


class AgentMonitorChangeField(BaseModel):
    """Field reference on a change item."""

    id: str
    name: Optional[str] = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class AgentMonitorChange(BaseModel):
    """One content change from the monitor's change feed."""

    type: Literal["content.upserted"]
    entity: AgentMonitorChangeEntity
    field: AgentMonitorChangeField
    content: AgentMonitorContent
    version: int
    created_at: str = Field(alias="createdAt")
    """ISO-8601 commit time of the change event."""

    model_config = {"populate_by_name": True, "extra": "allow"}


class AgentMonitorEntityParam(BaseModel):
    """An entity to track. `domain` anchors entity resolution and must be unique per monitor."""

    name: str
    domain: str
    """Resolution anchor: entities resolve by first-party or domain-verified evidence."""
    description: Optional[str] = None
    """Extra disambiguation context for entity resolution of ambiguous names."""

    model_config = {"populate_by_name": True, "extra": "allow"}


class AgentMonitorFieldParam(BaseModel):
    """A field to keep fresh. Dynamic (the default) unless declared `mode: "static"`."""

    name: str
    description: str
    type: Optional[Union[AgentMonitorFieldValueType, str]] = None
    """The type of the field's cell values; defaults to "string". Cell values
    are normalized to the declared type best-effort on write, never rejected —
    but declaring an unsupported type (e.g. "object") is a 400.
    "static"/"dynamic" are accepted as deprecated aliases of `mode`; declaring
    both spellings is a 400."""
    mode: Optional[AgentMonitorFieldMode] = None
    """Deprecated: the static/dynamic knob is becoming internal-only."""

    model_config = {"populate_by_name": True, "extra": "allow"}


class ListAgentMonitorsResponse(BaseModel):
    object: Optional[str] = None
    data: List[AgentMonitor]
    has_more: bool = Field(alias="hasMore")
    next_cursor: Optional[str] = Field(default=None, alias="nextCursor")

    model_config = {"populate_by_name": True, "extra": "allow"}


class ListAgentMonitorEntitiesResponse(BaseModel):
    object: Optional[str] = None
    data: List[AgentMonitorEntityView]
    has_more: bool = Field(alias="hasMore")
    next_cursor: Optional[str] = Field(default=None, alias="nextCursor")
    version: int
    """Store head change token; "am I caught up?" display only, NOT the cursor."""

    model_config = {"populate_by_name": True, "extra": "allow"}


class ListAgentMonitorChangesResponse(BaseModel):
    object: Optional[str] = None
    data: List[AgentMonitorChange]
    has_more: bool = Field(alias="hasMore")
    next_cursor: Optional[str] = Field(default=None, alias="nextCursor")
    """Opaque; resume the feed from the last served change. None when data is empty."""
    version: int
    """Store head change token; "am I caught up?" display only, NOT the cursor."""

    model_config = {"populate_by_name": True, "extra": "allow"}


class DeletedAgentMonitor(BaseModel):
    id: str
    object: Optional[str] = None
    deleted: bool

    model_config = {"populate_by_name": True, "extra": "allow"}


class AgentMonitorSnapshotEntity(BaseModel):
    """One entity's snapshot result: populated field values plus the news sources read."""

    name: str
    fields: Dict[str, str]
    """Populated values by field name; fields with no update are absent."""
    source_urls: List[str] = Field(alias="sourceUrls")

    model_config = {"populate_by_name": True, "extra": "allow"}


class AgentMonitorSnapshotFailedEntity(BaseModel):
    name: str
    reason: str

    model_config = {"populate_by_name": True, "extra": "allow"}


class AgentMonitorSnapshot(BaseModel):
    """A snapshot job.

    `create` returns it as `running`, and `get` polls it to `completed`
    (result fields present) or `failed`. Jobs expire and read as 404 after
    `expires_at`.
    """

    id: str
    object: Optional[str] = None
    status: AgentMonitorSnapshotStatus
    start_time: str = Field(alias="startTime")
    """The snapshotted news window, echoed back as normalized ISO-8601 timestamps."""
    end_time: str = Field(alias="endTime")
    created_at: str = Field(alias="createdAt")
    expires_at: str = Field(alias="expiresAt")
    data: Optional[List[AgentMonitorSnapshotEntity]] = None
    failed_entities: Optional[List[AgentMonitorSnapshotFailedEntity]] = Field(
        default=None, alias="failedEntities"
    )
    warnings: Optional[List[str]] = None
    """Caveats about how the snapshot was computed, e.g. static fields ignoring the window."""
    error: Optional[str] = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class AgentMonitorSnapshotFailedError(RuntimeError):
    """Raised when create_and_wait reaches a failed Agent Monitor snapshot."""

    snapshot: AgentMonitorSnapshot

    def __init__(self, snapshot: AgentMonitorSnapshot):
        message = (
            snapshot.error
            if snapshot.error is not None
            else f"Agent monitor snapshot {snapshot.id} failed"
        )
        super().__init__(message)
        self.snapshot = snapshot
