from __future__ import annotations

from typing import Annotated, Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, RootModel


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
        Literal["neural", "keyword", "auto", "fast"], Field(alias="searchType")
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


ResearchOperation = Annotated[
    Union[ResearchThinkOperation, ResearchSearchOperation, ResearchCrawlOperation],
    Field(discriminator="type"),
]


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


class ResearchOutputEvent(BaseModel):
    event_type: Annotated[Literal["research-output"], Field(alias="eventType")]
    research_id: Annotated[str, Field(alias="researchId")]
    created_at: Annotated[
        float, Field(alias="createdAt", description="Milliseconds since epoch time")
    ]
    output: Annotated[
        Union[ResearchOutputCompleted, ResearchOutputFailed],
        Field(discriminator="output_type"),
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


class ResearchPlanOutputEvent(BaseModel):
    event_type: Annotated[Literal["plan-output"], Field(alias="eventType")]
    research_id: Annotated[str, Field(alias="researchId")]
    plan_id: Annotated[str, Field(alias="planId")]
    created_at: Annotated[
        float, Field(alias="createdAt", description="Milliseconds since epoch time")
    ]
    output: Annotated[
        Union[ResearchPlanOutputTasks, ResearchPlanOutputStop],
        Field(discriminator="output_type"),
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
ResearchEvent = Union[ResearchMetaEvent, ResearchPlanEvent, ResearchTaskEvent]


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
        Literal["exa-research", "exa-research-pro"],
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


ResearchDto = Annotated[
    Union[
        ResearchPendingDto,
        ResearchRunningDto,
        ResearchCompletedDto,
        ResearchCanceledDto,
        ResearchFailedDto,
    ],
    Field(discriminator="status"),
]


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
    model: Literal["exa-research", "exa-research-pro"] = "exa-research"
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
