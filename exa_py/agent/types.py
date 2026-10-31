"""Types for the Exa Agent API."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field


AGENT_BETA_HEADER = "agent-2026-05-07"
AGENT_MAX_EFFORT_BETA = "agent-max-effort-2026-07-27"

KnownAgentRunStatus = Literal["queued", "running", "completed", "failed", "cancelled"]
AgentRunStatus = Union[KnownAgentRunStatus, str]
"""Agent run status. A value not in ``KnownAgentRunStatus`` is kept as a string."""

KnownAgentStopReason = Literal[
    "schema_satisfied",
    "budget_reached",
    "time_limit_reached",
    "token_limit_reached",
    "iteration_limit_reached",
    "stopped",
    "error",
    "cancelled",
]
AgentStopReason = Union[KnownAgentStopReason, str]
"""Why an Agent run stopped. A value not in ``KnownAgentStopReason`` is kept as a string."""

KnownAgentConfidence = Literal["low", "medium", "high"]
AgentConfidence = Union[KnownAgentConfidence, str]
"""Confidence of a grounding entry. A value not in ``KnownAgentConfidence`` is kept as a string."""
AgentEffort = Literal[
    "minimal", "low", "medium", "high", "xhigh", "auto", "ultra", "max"
]

AgentDataSourceProvider = str
"""Identifier of an Exa Connect data provider."""


class AgentDataSource(BaseModel):
    """Exa Connect data source to enable for an Agent run.

    See https://exa.ai/docs/agent/connect/overview for available providers.
    """

    provider: AgentDataSourceProvider

    model_config = {"populate_by_name": True, "extra": "allow"}


class AgentInput(BaseModel):
    data: Optional[List[Dict[str, Any]]] = None
    exclusion: Optional[List[Dict[str, Any]]] = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class AgentGroundingCitation(BaseModel):
    url: str
    title: Optional[str] = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class AgentGroundingEntry(BaseModel):
    field: str
    citations: List[AgentGroundingCitation]
    score: Optional[float] = None
    confidence: Optional[AgentConfidence] = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class AgentOutput(BaseModel):
    text: Optional[str] = None
    structured: Optional[Any] = None
    grounding: Optional[List[AgentGroundingEntry]] = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class AgentUsage(BaseModel):
    """Billed usage for an Agent run.

    When an ``auto`` or ``ultra`` run's metered cost exceeds its budget, the run
    is billed the budget and each quantity except ``data_sources`` is scaled down
    in proportion, so quantities can be fractional. A whole quantity stays an
    ``int``.
    """

    agent_compute_units: Optional[float] = Field(default=None, alias="agentComputeUnits")
    searches: Optional[Union[int, float]] = None
    emails: Optional[Union[int, float]] = None
    phone_numbers: Optional[Union[int, float]] = Field(default=None, alias="phoneNumbers")
    data_sources: Optional[Dict[str, int]] = Field(default=None, alias="dataSources")
    """Per-provider tool call counts for Exa Connect data sources used during the run."""

    model_config = {"populate_by_name": True, "extra": "allow"}


class AgentCostDollars(BaseModel):
    total: Optional[float] = None
    agent_compute: Optional[float] = Field(default=None, alias="agentCompute")
    search: Optional[float] = None
    emails: Optional[float] = None
    phone_numbers: Optional[float] = Field(default=None, alias="phoneNumbers")
    data_sources: Optional[Dict[str, float]] = Field(default=None, alias="dataSources")
    """Per-provider cost in dollars for Exa Connect data sources used during the run."""

    model_config = {"populate_by_name": True, "extra": "allow"}


class AgentError(BaseModel):
    type: Optional[str] = None
    code: Optional[str] = None
    message: Optional[str] = None
    path: Optional[str] = None
    keyword: Optional[str] = None
    expected: Optional[Any] = None
    actual: Optional[Any] = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class AgentBudget(BaseModel):
    """Per-run spend ceiling for the metered `auto` and `ultra` efforts."""

    max_cost_dollars: Optional[float] = Field(
        default=None,
        alias="maxCostDollars",
        description=(
            "Maximum spend for the run in US dollars, from 1 to 100. Only for "
            "`auto` and `ultra` effort. Defaults to 5 for `auto` and 20 for "
            "`ultra`."
        ),
    )
    max_duration_seconds: Optional[int] = Field(
        default=None,
        alias="maxDurationSeconds",
        description=(
            "Soft wall-clock ceiling in seconds (300-10,800). "
            "Only accepted for `ultra`."
        ),
    )

    model_config = {"populate_by_name": True, "extra": "allow"}


class AgentRun(BaseModel):
    id: str
    object: Optional[str] = None
    status: AgentRunStatus
    stop_reason: Optional[AgentStopReason] = Field(default=None, alias="stopReason")
    created_at: Optional[str] = Field(default=None, alias="createdAt")
    completed_at: Optional[str] = Field(default=None, alias="completedAt")
    request: Optional[Dict[str, Any]] = None
    output: Optional[AgentOutput] = None
    usage: Optional[AgentUsage] = None
    cost_dollars: Optional[AgentCostDollars] = Field(default=None, alias="costDollars")
    error: Optional[AgentError] = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class AgentRunFailedError(RuntimeError):
    """Raised when create_and_wait reaches a failed Agent run."""

    run: AgentRun

    def __init__(self, run: AgentRun):
        message = (
            run.error.message
            if run.error is not None and run.error.message is not None
            else f"Agent run {run.id} failed"
        )
        super().__init__(message)
        self.run = run


class AgentRunCancelledError(RuntimeError):
    """Raised when create_and_wait reaches a cancelled Agent run."""

    run: AgentRun

    def __init__(self, run: AgentRun):
        super().__init__(f"Agent run {run.id} was cancelled")
        self.run = run


class ListAgentRunsResponse(BaseModel):
    object: Optional[str] = None
    data: List[AgentRun]
    has_more: bool = Field(alias="hasMore")
    next_cursor: Optional[str] = Field(default=None, alias="nextCursor")

    model_config = {"populate_by_name": True, "extra": "allow"}


class DeletedAgentRun(BaseModel):
    id: str
    object: Optional[str] = None
    deleted: bool

    model_config = {"populate_by_name": True, "extra": "allow"}


class AgentEvent(BaseModel):
    id: Optional[str] = None
    event: str
    data: Dict[str, Any]
    created_at: Optional[str] = Field(default=None, alias="createdAt")

    model_config = {"populate_by_name": True, "extra": "allow"}


class ListAgentRunEventsResponse(BaseModel):
    object: Optional[str] = None
    data: List[AgentEvent]
    has_more: bool = Field(alias="hasMore")
    next_cursor: Optional[str] = Field(default=None, alias="nextCursor")

    model_config = {"populate_by_name": True, "extra": "allow"}


class CreateAgentRunParams(BaseModel):
    query: str
    system_prompt: Optional[str] = Field(default=None, alias="systemPrompt")
    input: Optional[AgentInput] = None
    output_schema: Optional[Dict[str, Any]] = Field(default=None, alias="outputSchema")
    effort: Optional[AgentEffort] = None
    budget: Optional[AgentBudget] = None
    previous_run_id: Optional[str] = Field(default=None, alias="previousRunId")
    metadata: Optional[Dict[str, Any]] = None
    data_sources: Optional[List[AgentDataSource]] = Field(default=None, alias="dataSources")
    """Exa Connect data providers to enable for the run."""
    user_identifier: Optional[str] = Field(default=None, alias="userIdentifier")
    """Opaque, non-personal identifier of the end user the run is made on behalf of."""

    model_config = {"populate_by_name": True, "extra": "allow"}
