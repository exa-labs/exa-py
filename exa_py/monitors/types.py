"""Types for the Search Monitors API."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field


# --- Enums as Literal types ---

KnownSearchMonitorStatus = Literal["active", "paused", "disabled"]
SearchMonitorStatus = Union[KnownSearchMonitorStatus, str]
"""Search Monitor status. A value not in ``KnownSearchMonitorStatus`` is kept as a string."""

KnownSearchMonitorRunStatus = Literal[
    "pending", "running", "completed", "failed", "cancelled"
]
SearchMonitorRunStatus = Union[KnownSearchMonitorRunStatus, str]
"""Search Monitor run status. A value not in ``KnownSearchMonitorRunStatus`` is kept as a string."""

KnownSearchMonitorRunFailReason = Literal[
    "api_key_invalid",
    "insufficient_credits",
    "invalid_params",
    "rate_limited",
    "source_not_available",
    "forbidden",
    "search_unavailable",
    "search_failed",
    "internal_error",
]
SearchMonitorRunFailReason = Union[KnownSearchMonitorRunFailReason, str]
"""Why a monitor run failed. A value not in ``KnownSearchMonitorRunFailReason`` is kept as a string."""

KnownSearchMonitorWebhookEvent = Literal[
    "monitor.created",
    "monitor.updated",
    "monitor.deleted",
    "monitor.run.created",
    "monitor.run.completed",
]
SearchMonitorWebhookEvent = Union[KnownSearchMonitorWebhookEvent, str]
"""Search Monitor webhook event. A value not in ``KnownSearchMonitorWebhookEvent`` is kept as a string."""


# --- Contents types ---

VERBOSITY_OPTION = Literal["compact", "standard", "full"]

SECTION_TAG = Literal[
    "unspecified", "header", "navigation", "banner",
    "body", "sidebar", "footer", "metadata",
]

LIVECRAWL_OPTION = Literal["never", "always", "fallback", "auto", "preferred"]


class SearchMonitorTextContents(BaseModel):
    """Options for text extraction in monitor results."""

    max_characters: Optional[int] = Field(default=None, alias="maxCharacters")
    include_html_tags: Optional[bool] = Field(default=None, alias="includeHtmlTags")
    verbosity: Optional[Union[VERBOSITY_OPTION, str]] = None
    include_sections: Optional[List[Union[SECTION_TAG, str]]] = Field(
        default=None, alias="includeSections"
    )
    exclude_sections: Optional[List[Union[SECTION_TAG, str]]] = Field(
        default=None, alias="excludeSections"
    )

    model_config = {"populate_by_name": True}


class SearchMonitorHighlightsContents(BaseModel):
    """Options for highlights extraction in monitor results."""

    query: Optional[str] = None
    max_characters: Optional[int] = Field(default=None, alias="maxCharacters")
    num_sentences: Optional[int] = Field(
        default=None,
        alias="numSentences",  # DEPRECATED FIELD: legacy API key.
        deprecated=(
            "Deprecated. Use max_characters."
        ),
        description=(
            "Deprecated. Use max_characters."
        ),
    )
    highlights_per_url: Optional[int] = Field(
        default=None,
        alias="highlightsPerUrl",  # DEPRECATED FIELD: legacy API key.
        deprecated=(
            "Deprecated. Use max_characters."
        ),
        description=(
            "Deprecated. Use max_characters."
        ),
    )

    model_config = {"populate_by_name": True}


class SearchMonitorSummaryContents(BaseModel):
    """Options for summary generation in monitor results."""

    query: Optional[str] = None
    schema_: Optional[Dict[str, Any]] = Field(default=None, alias="schema")

    model_config = {"populate_by_name": True}


class SearchMonitorExtrasContents(BaseModel):
    """Options for additional data extraction in monitor results."""

    links: Optional[int] = None
    image_links: Optional[int] = Field(default=None, alias="imageLinks")

    model_config = {"populate_by_name": True}


class SearchMonitorContents(BaseModel):
    """Options for retrieving page contents in monitor results.

    Mirrors the main search ContentsOptions. Text, highlights, and summary
    accept either True (for defaults) or an options object. The context field is
    deprecated and kept only for backward compatibility.
    """

    text: Optional[Union[bool, SearchMonitorTextContents]] = None
    highlights: Optional[Union[bool, SearchMonitorHighlightsContents]] = None
    summary: Optional[Union[bool, SearchMonitorSummaryContents]] = None
    extras: Optional[SearchMonitorExtrasContents] = None
    context: Optional[Union[bool, Dict[str, Any]]] = Field(
        default=None,
        deprecated=(
            "Deprecated. Use highlights or text."
        ),
        description=(
            "Deprecated. Use highlights or text."
        ),
    )
    livecrawl: Optional[Union[LIVECRAWL_OPTION, str]] = Field(
        default=None,
        deprecated="Deprecated. Use max_age_hours instead.",
        description=(
            "Deprecated. Use max_age_hours instead. Does not guarantee freshly "
            "fetched content. Cannot be combined with max_age_hours."
        ),
    )
    livecrawl_timeout: Optional[int] = Field(default=None, alias="livecrawlTimeout")
    max_age_hours: Optional[int] = Field(default=None, alias="maxAgeHours")
    filter_empty_results: Optional[bool] = Field(
        default=None, alias="filterEmptyResults"
    )
    subpages: Optional[int] = None
    subpage_target: Optional[Union[str, List[str]]] = Field(
        default=None, alias="subpageTarget"
    )

    model_config = {"populate_by_name": True}


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
    contents: Optional[SearchMonitorContents] = None

    model_config = {"populate_by_name": True}


class SearchMonitorTrigger(BaseModel):
    type: Union[Literal["interval"], str]
    period: str

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
    confidence: Union[Literal["low", "medium", "high"], str]

    model_config = {"populate_by_name": True}


class SearchMonitorRunOutput(BaseModel):
    results: Optional[List[Dict[str, Any]]] = None
    content: Optional[Union[str, Dict[str, Any]]] = None
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
