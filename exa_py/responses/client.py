"""Synchronous and asynchronous clients for Exa's Responses API."""

from __future__ import annotations

from typing import Any, Dict, Iterable, Literal, Optional, Union, overload

from .types import (
    AgentResponseEffort,
    AgentResponseModel,
    Response,
    ResponseInputParam,
    ResponseReasoningParam,
    ResponseTextConfigParam,
)


class ResponsesClient:
    """Synchronous client for OpenAI-compatible Agent responses."""

    def __init__(self, client: Any):
        self._client = client

    @overload
    def create(
        self,
        *,
        input: ResponseInputParam,
        model: Union[AgentResponseModel, str] = "agent",
        reasoning: Optional[ResponseReasoningParam] = None,
        instructions: Optional[str] = None,
        previous_response_id: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        text: Optional[ResponseTextConfigParam] = None,
        stream: Literal[False] = False,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        tools: Optional[Iterable[Dict[str, Any]]] = None,
        tool_choice: Optional[Any] = None,
        max_output_tokens: Optional[int] = None,
        store: Optional[bool] = None,
        **kwargs: Any,
    ) -> Response: ...

    def create(
        self,
        *,
        input: ResponseInputParam,
        model: Union[AgentResponseModel, str] = "agent",
        reasoning: Optional[ResponseReasoningParam] = None,
        instructions: Optional[str] = None,
        previous_response_id: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        text: Optional[ResponseTextConfigParam] = None,
        stream: bool = False,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        tools: Optional[Iterable[Dict[str, Any]]] = None,
        tool_choice: Optional[Any] = None,
        max_output_tokens: Optional[int] = None,
        store: Optional[bool] = None,
        **kwargs: Any,
    ) -> Response:
        """Create a non-streaming Agent response.

        Args:
            input: The user input string or Responses message list.
            model: The Responses model name. Defaults to ``"agent"``.
            reasoning: Optional reasoning configuration. ``reasoning["effort"]``
                maps to Agent effort modes: ``minimal``, ``low``, ``medium``, ``high``,
                ``xhigh``, or ``auto``.
            instructions: Optional system or developer instructions.
            previous_response_id: Optional previous response ID for follow-up context.
            metadata: Optional metadata to attach to the response.
            text: Optional text output configuration, including JSON schema format.
            stream: Must be ``False``. Streaming Responses are not supported yet.
            temperature: Accepted for OpenAI compatibility and ignored by the API.
            top_p: Accepted for OpenAI compatibility and ignored by the API.
            tools: Accepted for OpenAI compatibility and ignored by the API.
            tool_choice: Accepted for OpenAI compatibility and ignored by the API.
            max_output_tokens: Accepted for OpenAI compatibility and ignored by the API.
            store: Optional OpenAI-compatible store flag.
            **kwargs: Additional OpenAI-compatible fields forwarded to the API.

        Returns:
            A Responses-compatible object with ``output_text``.

        Examples:
            from exa_py import Exa

            exa = Exa("EXA_API_KEY")
            response = exa.responses.create(
                model="agent",
                input="Find companies building browser automation tools.",
                reasoning={"effort": "minimal"},
            )
            print(response.output_text)
        """
        if stream:
            raise ValueError("Streaming Responses are not supported yet.")

        payload = {
            "input": input,
            "model": model,
            "reasoning": reasoning,
            "instructions": instructions,
            "previous_response_id": previous_response_id,
            "metadata": metadata,
            "text": text,
            "temperature": temperature,
            "top_p": top_p,
            "tools": list(tools) if tools is not None else None,
            "tool_choice": tool_choice,
            "max_output_tokens": max_output_tokens,
            "store": store,
            **kwargs,
        }
        response = self._client.request(
            "/v1/responses",
            data={key: value for key, value in payload.items() if value is not None},
            method="POST",
        )
        return Response.model_validate(response)


class AsyncResponsesClient:
    """Asynchronous client for OpenAI-compatible Agent responses."""

    def __init__(self, client: Any):
        self._client = client

    async def create(
        self,
        *,
        input: ResponseInputParam,
        model: Union[AgentResponseModel, str] = "agent",
        reasoning: Optional[ResponseReasoningParam] = None,
        instructions: Optional[str] = None,
        previous_response_id: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        text: Optional[ResponseTextConfigParam] = None,
        stream: bool = False,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        tools: Optional[Iterable[Dict[str, Any]]] = None,
        tool_choice: Optional[Any] = None,
        max_output_tokens: Optional[int] = None,
        store: Optional[bool] = None,
        **kwargs: Any,
    ) -> Response:
        """Create a non-streaming Agent response asynchronously.

        Args:
            input: The user input string or Responses message list.
            model: The Responses model name. Defaults to ``"agent"``.
            reasoning: Optional reasoning configuration. ``reasoning["effort"]``
                maps to Agent effort modes: ``minimal``, ``low``, ``medium``, ``high``,
                ``xhigh``, or ``auto``.
            instructions: Optional system or developer instructions.
            previous_response_id: Optional previous response ID for follow-up context.
            metadata: Optional metadata to attach to the response.
            text: Optional text output configuration, including JSON schema format.
            stream: Must be ``False``. Streaming Responses are not supported yet.
            temperature: Accepted for OpenAI compatibility and ignored by the API.
            top_p: Accepted for OpenAI compatibility and ignored by the API.
            tools: Accepted for OpenAI compatibility and ignored by the API.
            tool_choice: Accepted for OpenAI compatibility and ignored by the API.
            max_output_tokens: Accepted for OpenAI compatibility and ignored by the API.
            store: Optional OpenAI-compatible store flag.
            **kwargs: Additional OpenAI-compatible fields forwarded to the API.

        Returns:
            A Responses-compatible object with ``output_text``.

        Examples:
            from exa_py import AsyncExa

            exa = AsyncExa("EXA_API_KEY")
            response = await exa.responses.create(
                model="agent",
                input="Find companies building browser automation tools.",
                reasoning={"effort": "minimal"},
            )
            print(response.output_text)
        """
        if stream:
            raise ValueError("Streaming Responses are not supported yet.")

        payload = {
            "input": input,
            "model": model,
            "reasoning": reasoning,
            "instructions": instructions,
            "previous_response_id": previous_response_id,
            "metadata": metadata,
            "text": text,
            "temperature": temperature,
            "top_p": top_p,
            "tools": list(tools) if tools is not None else None,
            "tool_choice": tool_choice,
            "max_output_tokens": max_output_tokens,
            "store": store,
            **kwargs,
        }
        response = await self._client.async_request(
            "/v1/responses",
            data={key: value for key, value in payload.items() if value is not None},
            method="POST",
        )
        return Response.model_validate(response)
