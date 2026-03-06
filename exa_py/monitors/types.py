"""Types for the Search Monitors API."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# --- Enums as Literal types ---

SearchMonitorStatus = Literal["active", "paused", "disabled"]

SearchMonitorRunStatus = Literal[
    "pending", "running", "completed", "failed", "cancelled"
]

SearchMonitorRunFailReason = Literal[
    "api_key_invalid",
    "insufficient_credits",
    "invalid_params",
    "rate_limited",
    "search_unavailable",
    "search_failed",
    "internal_error",
]

SearchMonitorWebhookEvent = Literal[
    "monitor.created",
    "monitor.updated",
    "monitor.deleted",
    "monitor.run.created",
    "monitor.run.completed",
]


# --- Nested types ---


class SearchMonitorSearch(BaseModel):
    query: str
    num_results: Optional[int] = Field(default=None, alias="numResults")
    include_domains: Optional[List[str]] = Field(
        default=None, alias="includeDomains"
    )
    exclude_domains: Optional[List[str]] = Field(
        default=None, alias="excludeDomains"
    )
    include_text: Optional[List[str]] = Field(default=None, alias="includeText")
    exclude_text: Optional[List[str]] = Field(default=None, alias="excludeText")

    model_config = {"populate_by_name": True}


class SearchMonitorTrigger(BaseModel):
    type: Literal["cron"]
    expression: str
    timezone: Optional[str] = None

    model_config = {"populate_by_name": True}


class SearchMonitorWebhook(BaseModel):
    url: str
    events: Optional[List[SearchMonitorWebhookEvent]] = None

    model_config = {"populate_by_name": True}


class GroundingCitation(BaseModel):
    url: str
    title: str

    model_config = {"populate_by_name": True}


class GroundingEntry(BaseModel):
    field: str
    citations: List[GroundingCitation]
    confidence: Literal["low", "medium", "high"]

    model_config = {"populate_by_name": True}


class SearchMonitorRunOutput(BaseModel):
    results: Optional[List[Dict[str, Any]]] = None
    content: Optional[str] = None
    grounding: Optional[List[GroundingEntry]] = None

    model_config = {"populate_by_name": True}


# --- Main resource types ---


class SearchMonitor(BaseModel):
    id: str
    name: Optional[str] = None
    status: SearchMonitorStatus
    search: SearchMonitorSearch
    trigger: Optional[SearchMonitorTrigger] = None
    output_schema: Optional[Dict[str, Any]] = Field(
        default=None, alias="outputSchema"
    )
    metadata: Optional[Dict[str, str]] = None
    webhook: SearchMonitorWebhook
    next_run_at: Optional[str] = Field(default=None, alias="nextRunAt")
    created_at: str = Field(alias="createdAt")
    updated_at: str = Field(alias="updatedAt")

    model_config = {"populate_by_name": True}


class CreateSearchMonitorResponse(SearchMonitor):
    webhook_secret: str = Field(alias="webhookSecret")

    model_config = {"populate_by_name": True}


class SearchMonitorRun(BaseModel):
    id: str
    monitor_id: str = Field(alias="monitorId")
    status: SearchMonitorRunStatus
    output: Optional[SearchMonitorRunOutput] = None
    fail_reason: Optional[SearchMonitorRunFailReason] = Field(
        default=None, alias="failReason"
    )
    started_at: Optional[str] = Field(default=None, alias="startedAt")
    completed_at: Optional[str] = Field(default=None, alias="completedAt")
    failed_at: Optional[str] = Field(default=None, alias="failedAt")
    cancelled_at: Optional[str] = Field(default=None, alias="cancelledAt")
    duration_ms: Optional[int] = Field(default=None, alias="durationMs")
    created_at: str = Field(alias="createdAt")
    updated_at: str = Field(alias="updatedAt")

    model_config = {"populate_by_name": True}


# --- Request params ---


class CreateSearchMonitorParams(BaseModel):
    name: Optional[str] = None
    search: SearchMonitorSearch
    trigger: Optional[SearchMonitorTrigger] = None
    output_schema: Optional[Dict[str, Any]] = Field(
        default=None, alias="outputSchema"
    )
    metadata: Optional[Dict[str, str]] = None
    webhook: SearchMonitorWebhook

    model_config = {"populate_by_name": True}


class UpdateSearchMonitorParams(BaseModel):
    name: Optional[str] = None
    status: Optional[SearchMonitorStatus] = None
    search: Optional[SearchMonitorSearch] = None
    trigger: Optional[SearchMonitorTrigger] = None
    output_schema: Optional[Dict[str, Any]] = Field(
        default=None, alias="outputSchema"
    )
    metadata: Optional[Dict[str, str]] = None
    webhook: Optional[SearchMonitorWebhook] = None

    model_config = {"populate_by_name": True}


# --- Response types ---


class TriggerSearchMonitorResponse(BaseModel):
    triggered: bool

    model_config = {"populate_by_name": True}


class ListSearchMonitorsResponse(BaseModel):
    data: List[SearchMonitor]
    has_more: bool = Field(alias="hasMore")
    next_cursor: Optional[str] = Field(default=None, alias="nextCursor")

    model_config = {"populate_by_name": True}


class ListSearchMonitorRunsResponse(BaseModel):
    data: List[SearchMonitorRun]
    has_more: bool = Field(alias="hasMore")
    next_cursor: Optional[str] = Field(default=None, alias="nextCursor")

    model_config = {"populate_by_name": True}
