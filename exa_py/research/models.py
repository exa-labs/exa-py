from __future__ import annotations

from typing import Annotated, Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, RootModel, Tag

from .._open_union import UNKNOWN_TAG, tag_discriminator


KnownResearchModel = Literal["exa-research-fast", "exa-research", "exa-research-pro"]
ResearchModel = Union[KnownResearchModel, str]
"""Research model. A value not in ``KnownResearchModel`` is kept as a string."""


class CostDollars(BaseModel):
    total: float
    num_pages: Annotated[float, Field(alias="numPages")]
    num_searches: Annotated[float, Field(alias="numSearches")]
    reasoning_tokens: Annotated[float, Field(alias="reasoningTokens")]


class Result(BaseModel):
    url: str


class ResearchThinkOperation(BaseModel):
    type: Literal["think"]
    content: str


class ResearchSearchOperation(BaseModel):
    type: Literal["search"]
    search_type: Annotated[
        Union[Literal["neural", "keyword", "auto", "fast"], str],
        Field(alias="searchType"),
    ]
    query: str
    results: List[Result]
    page_tokens: Annotated[float, Field(alias="pageTokens")]
    goal: Optional[str] = None


class ResearchCrawlOperation(BaseModel):
    type: Literal["crawl"]
    result: Result
    page_tokens: Annotated[float, Field(alias="pageTokens")]
    goal: Optional[str] = None


class ResearchUnknownOperation(BaseModel):
    """An operation whose ``type`` this SDK version does not list. Its other fields are kept as extra attributes."""

    type: str

    model_config = ConfigDict(extra="allow")


ResearchOperation = Annotated[
    Union[
        Annotated[ResearchThinkOperation, Tag("think")],
        Annotated[ResearchSearchOperation, Tag("search")],
        Annotated[ResearchCrawlOperation, Tag("crawl")],
        Annotated[ResearchUnknownOperation, Tag(UNKNOWN_TAG)],
    ],
    tag_discriminator(
        "type", ResearchThinkOperation, ResearchSearchOperation, ResearchCrawlOperation
    ),
]
"""One operation of a research plan or task. A ``type`` this SDK version does not list parses as ``ResearchUnknownOperation``."""


class ResearchDefinitionEvent(BaseModel):
    event_type: Annotated[Literal["research-definition"], Field(alias="eventType")]
    research_id: Annotated[str, Field(alias="researchId")]
    created_at: Annotated[
        float, Field(alias="createdAt", description="Milliseconds since epoch time")
    ]
    instructions: str
    output_schema: Annotated[Optional[Dict[str, Any]], Field(alias="outputSchema")] = (
        None
    )


class ResearchOutputCompleted(BaseModel):
    output_type: Annotated[Literal["completed"], Field(alias="outputType")]
    content: str
    cost_dollars: Annotated[CostDollars, Field(alias="costDollars")]
    parsed: Optional[Dict[str, Any]] = None


class ResearchOutputFailed(BaseModel):
    output_type: Annotated[Literal["failed"], Field(alias="outputType")]
    error: str


class ResearchUnknownOutput(BaseModel):
    """An output whose ``outputType`` this SDK version does not list. Its other fields are kept as extra attributes."""

    output_type: Annotated[str, Field(alias="outputType")]

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class ResearchOutputEvent(BaseModel):
    event_type: Annotated[Literal["research-output"], Field(alias="eventType")]
    research_id: Annotated[str, Field(alias="researchId")]
    created_at: Annotated[
        float, Field(alias="createdAt", description="Milliseconds since epoch time")
    ]
    output: Annotated[
        Union[
            Annotated[ResearchOutputCompleted, Tag("completed")],
            Annotated[ResearchOutputFailed, Tag("failed")],
            Annotated[ResearchUnknownOutput, Tag(UNKNOWN_TAG)],
        ],
        tag_discriminator("output_type", ResearchOutputCompleted, ResearchOutputFailed),
    ]


class ResearchPlanDefinitionEvent(BaseModel):
    event_type: Annotated[Literal["plan-definition"], Field(alias="eventType")]
    research_id: Annotated[str, Field(alias="researchId")]
    plan_id: Annotated[str, Field(alias="planId")]
    created_at: Annotated[
        float, Field(alias="createdAt", description="Milliseconds since epoch time")
    ]


class ResearchPlanOperationEvent(BaseModel):
    event_type: Annotated[Literal["plan-operation"], Field(alias="eventType")]
    research_id: Annotated[str, Field(alias="researchId")]
    plan_id: Annotated[str, Field(alias="planId")]
    operation_id: Annotated[str, Field(alias="operationId")]
    created_at: Annotated[
        float, Field(alias="createdAt", description="Milliseconds since epoch time")
    ]
    data: ResearchOperation


class ResearchPlanOutputTasks(BaseModel):
    output_type: Annotated[Literal["tasks"], Field(alias="outputType")]
    reasoning: str
    tasks_instructions: Annotated[List[str], Field(alias="tasksInstructions")]


class ResearchPlanOutputStop(BaseModel):
    output_type: Annotated[Literal["stop"], Field(alias="outputType")]
    reasoning: str


class ResearchUnknownPlanOutput(ResearchUnknownOutput):
    """A plan output whose ``outputType`` this SDK version does not list. Its other fields are kept as extra attributes."""

    reasoning: str


class ResearchPlanOutputEvent(BaseModel):
    event_type: Annotated[Literal["plan-output"], Field(alias="eventType")]
    research_id: Annotated[str, Field(alias="researchId")]
    plan_id: Annotated[str, Field(alias="planId")]
    created_at: Annotated[
        float, Field(alias="createdAt", description="Milliseconds since epoch time")
    ]
    output: Annotated[
        Union[
            Annotated[ResearchPlanOutputTasks, Tag("tasks")],
            Annotated[ResearchPlanOutputStop, Tag("stop")],
            Annotated[ResearchUnknownPlanOutput, Tag(UNKNOWN_TAG)],
        ],
        tag_discriminator("output_type", ResearchPlanOutputTasks, ResearchPlanOutputStop),
    ]


class ResearchTaskDefinitionEvent(BaseModel):
    event_type: Annotated[Literal["task-definition"], Field(alias="eventType")]
    research_id: Annotated[str, Field(alias="researchId")]
    plan_id: Annotated[str, Field(alias="planId")]
    task_id: Annotated[str, Field(alias="taskId")]
    created_at: Annotated[
        float, Field(alias="createdAt", description="Milliseconds since epoch time")
    ]
    instructions: str


class ResearchTaskOperationEvent(BaseModel):
    event_type: Annotated[Literal["task-operation"], Field(alias="eventType")]
    research_id: Annotated[str, Field(alias="researchId")]
    plan_id: Annotated[str, Field(alias="planId")]
    task_id: Annotated[str, Field(alias="taskId")]
    operation_id: Annotated[str, Field(alias="operationId")]
    created_at: Annotated[
        float, Field(alias="createdAt", description="Milliseconds since epoch time")
    ]
    data: ResearchOperation


class ResearchTaskOutput(BaseModel):
    output_type: Annotated[Literal["completed"], Field(alias="outputType")]
    content: str


class ResearchTaskOutputEvent(BaseModel):
    event_type: Annotated[Literal["task-output"], Field(alias="eventType")]
    research_id: Annotated[str, Field(alias="researchId")]
    plan_id: Annotated[str, Field(alias="planId")]
    task_id: Annotated[str, Field(alias="taskId")]
    created_at: Annotated[
        float, Field(alias="createdAt", description="Milliseconds since epoch time")
    ]
    output: ResearchTaskOutput


ResearchMetaEvent = Union[ResearchDefinitionEvent, ResearchOutputEvent]
ResearchPlanEvent = Union[
    ResearchPlanDefinitionEvent, ResearchPlanOperationEvent, ResearchPlanOutputEvent
]
ResearchTaskEvent = Union[
    ResearchTaskDefinitionEvent, ResearchTaskOperationEvent, ResearchTaskOutputEvent
]


class ResearchUnknownEvent(BaseModel):
    """An event whose ``eventType`` this SDK version does not list. Its other fields are kept as extra attributes."""

    event_type: Annotated[str, Field(alias="eventType")]
    research_id: Annotated[str, Field(alias="researchId")]
    created_at: Annotated[
        float,
        Field(alias="createdAt", description="Milliseconds since epoch time"),
    ]

    model_config = ConfigDict(extra="allow", populate_by_name=True)


ResearchEvent = Annotated[
    Union[
        Annotated[ResearchDefinitionEvent, Tag("research-definition")],
        Annotated[ResearchOutputEvent, Tag("research-output")],
        Annotated[ResearchPlanDefinitionEvent, Tag("plan-definition")],
        Annotated[ResearchPlanOperationEvent, Tag("plan-operation")],
        Annotated[ResearchPlanOutputEvent, Tag("plan-output")],
        Annotated[ResearchTaskDefinitionEvent, Tag("task-definition")],
        Annotated[ResearchTaskOperationEvent, Tag("task-operation")],
        Annotated[ResearchTaskOutputEvent, Tag("task-output")],
        Annotated[ResearchUnknownEvent, Tag(UNKNOWN_TAG)],
    ],
    tag_discriminator(
        "event_type",
        ResearchDefinitionEvent,
        ResearchOutputEvent,
        ResearchPlanDefinitionEvent,
        ResearchPlanOperationEvent,
        ResearchPlanOutputEvent,
        ResearchTaskDefinitionEvent,
        ResearchTaskOperationEvent,
        ResearchTaskOutputEvent,
    ),
]
"""Any research event. An ``eventType`` this SDK version does not list parses as ``ResearchUnknownEvent``."""


class ResearchOutput(BaseModel):
    content: str
    parsed: Optional[Dict[str, Any]] = None


class ResearchBaseDto(BaseModel):
    research_id: Annotated[
        str,
        Field(
            alias="researchId",
            description="The unique identifier for the research request",
        ),
    ]
    created_at: Annotated[
        float, Field(alias="createdAt", description="Milliseconds since epoch time")
    ]
    model: Annotated[
        ResearchModel,
        Field(description="The model used for the research request"),
    ] = "exa-research"
    instructions: Annotated[
        str, Field(description="The instructions given to this research request")
    ]
    output_schema: Annotated[Optional[Dict[str, Any]], Field(alias="outputSchema")] = (
        None
    )


class ResearchPendingDto(ResearchBaseDto):
    status: Literal["pending"]


class ResearchRunningDto(ResearchBaseDto):
    status: Literal["running"]
    events: Optional[List[ResearchEvent]] = None


class ResearchCompletedDto(ResearchBaseDto):
    status: Literal["completed"]
    finished_at: Annotated[
        float, Field(alias="createdAt", description="Milliseconds since epoch time")
    ]
    events: Optional[List[ResearchEvent]] = None
    output: ResearchOutput
    cost_dollars: Annotated[CostDollars, Field(alias="costDollars")]


class ResearchCanceledDto(ResearchBaseDto):
    status: Literal["canceled"]
    finished_at: Annotated[
        float, Field(alias="createdAt", description="Milliseconds since epoch time")
    ]
    events: Optional[List[ResearchEvent]] = None


class ResearchFailedDto(ResearchBaseDto):
    status: Literal["failed"]
    finished_at: Annotated[
        float, Field(alias="createdAt", description="Milliseconds since epoch time")
    ]
    events: Optional[List[ResearchEvent]] = None
    error: Annotated[
        str, Field(description="A message indicating why the request failed")
    ]


class ResearchUnknownDto(ResearchBaseDto):
    """A research request whose ``status`` this SDK version does not list. Its other fields are kept as extra attributes."""

    status: str

    model_config = ConfigDict(extra="allow", populate_by_name=True)


ResearchDto = Annotated[
    Union[
        Annotated[ResearchPendingDto, Tag("pending")],
        Annotated[ResearchRunningDto, Tag("running")],
        Annotated[ResearchCompletedDto, Tag("completed")],
        Annotated[ResearchCanceledDto, Tag("canceled")],
        Annotated[ResearchFailedDto, Tag("failed")],
        Annotated[ResearchUnknownDto, Tag(UNKNOWN_TAG)],
    ],
    tag_discriminator(
        "status",
        ResearchPendingDto,
        ResearchRunningDto,
        ResearchCompletedDto,
        ResearchCanceledDto,
        ResearchFailedDto,
    ),
]
"""A research request in any status. A ``status`` this SDK version does not list parses as ``ResearchUnknownDto``."""


class ListResearchResponseDto(BaseModel):
    data: Annotated[
        List[ResearchDto], Field(description="The list of research requests")
    ]
    has_more: Annotated[
        bool,
        Field(
            alias="hasMore",
            description="Whether there are more results to paginate through",
        ),
    ]
    next_cursor: Annotated[
        Optional[str],
        Field(
            alias="nextCursor",
            description="The cursor to paginate through the next set of results",
        ),
    ]


class ResearchCreateRequestDto(BaseModel):
    model: KnownResearchModel = "exa-research"
    instructions: Annotated[
        str,
        Field(
            description="Instructions for what research should be conducted",
            max_length=4096,
        ),
    ]
    output_schema: Annotated[Optional[Dict[str, Any]], Field(alias="outputSchema")] = (
        None
    )


ResearchDtoClass = RootModel[ResearchDto]
ResearchCreateRequestDtoClass = ResearchCreateRequestDto
ResearchEventDtoClass = RootModel[ResearchEvent]
ResearchOperationDtoClass = RootModel[ResearchOperation]


__all__ = [
    "CostDollars",
    "Result",
    "ResearchThinkOperation",
    "ResearchSearchOperation",
    "ResearchCrawlOperation",
    "ResearchOperation",
    "ResearchDefinitionEvent",
    "ResearchOutputCompleted",
    "ResearchOutputFailed",
    "ResearchOutputEvent",
    "ResearchPlanDefinitionEvent",
    "ResearchPlanOperationEvent",
    "ResearchPlanOutputTasks",
    "ResearchPlanOutputStop",
    "ResearchPlanOutputEvent",
    "ResearchTaskDefinitionEvent",
    "ResearchTaskOperationEvent",
    "ResearchTaskOutput",
    "ResearchTaskOutputEvent",
    "ResearchMetaEvent",
    "KnownResearchModel",
    "ResearchModel",
    "ResearchUnknownDto",
    "ResearchUnknownEvent",
    "ResearchUnknownOperation",
    "ResearchUnknownOutput",
    "ResearchUnknownPlanOutput",
    "ResearchPlanEvent",
    "ResearchTaskEvent",
    "ResearchEvent",
    "ResearchOutput",
    "ResearchBaseDto",
    "ResearchPendingDto",
    "ResearchRunningDto",
    "ResearchCompletedDto",
    "ResearchCanceledDto",
    "ResearchFailedDto",
    "ResearchDto",
    "ListResearchResponseDto",
    "ResearchCreateRequestDto",
    "ResearchDtoClass",
    "ResearchCreateRequestDtoClass",
    "ResearchEventDtoClass",
    "ResearchOperationDtoClass",
]
