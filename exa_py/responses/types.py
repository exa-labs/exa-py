"""Types for Exa's OpenAI-compatible Responses API."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Sequence, Union

from pydantic import BaseModel, Field
from typing_extensions import TypedDict


AgentResponseModel = Literal["agent", "exa-agent"]
AgentResponseEffort = Literal["low", "medium", "high", "xhigh", "auto"]
ResponseStatus = Literal["completed", "failed", "incomplete", "queued", "running"]


class ResponseReasoningParam(TypedDict, total=False):
    effort: Optional[AgentResponseEffort]


class ResponseTextFormatParam(TypedDict, total=False):
    type: str
    name: str
    schema: Dict[str, Any]
    strict: bool


class ResponseTextConfigParam(TypedDict, total=False):
    format: ResponseTextFormatParam


class ResponseInputMessageParam(TypedDict, total=False):
    role: Literal["user", "assistant", "system", "developer"]
    content: Union[str, List[Dict[str, Any]]]
    type: Literal["message"]
    phase: Literal["commentary", "final_answer"]


ResponseInputParam = Union[str, Sequence[ResponseInputMessageParam]]


class ResponseOutputText(BaseModel):
    type: Literal["output_text"]
    text: str
    annotations: List[Any] = Field(default_factory=list)

    model_config = {"populate_by_name": True, "extra": "allow"}


class ResponseOutputMessage(BaseModel):
    id: Optional[str] = None
    type: Literal["message"]
    status: Literal["completed", "incomplete", "in_progress"]
    role: Literal["assistant"]
    content: List[ResponseOutputText]

    model_config = {"populate_by_name": True, "extra": "allow"}


class ResponseError(BaseModel):
    code: Optional[str] = None
    message: Optional[str] = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class ResponseIncompleteDetails(BaseModel):
    reason: Optional[str] = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class Response(BaseModel):
    id: str
    object: Literal["response"]
    created_at: int
    completed_at: Optional[int] = None
    status: ResponseStatus
    model: str
    output: List[ResponseOutputMessage]
    output_text: str = ""
    error: Optional[ResponseError] = None
    incomplete_details: Optional[ResponseIncompleteDetails] = None
    instructions: Optional[str] = None
    previous_response_id: Optional[str] = None
    metadata: Dict[str, str] = Field(default_factory=dict)
    tools: List[Any] = Field(default_factory=list)
    tool_choice: Any = None
    parallel_tool_calls: Optional[bool] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    reasoning: Optional[Dict[str, Any]] = None
    usage: Optional[Dict[str, Any]] = None

    model_config = {"populate_by_name": True, "extra": "allow"}

