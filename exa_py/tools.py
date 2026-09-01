"""Provider integrations for using Exa operations as model tools."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable, Mapping
from typing import Any, Optional

from pydantic import BaseModel, Field

DEFAULT_WEB_SEARCH_DESCRIPTION = (
    "Search the web for up-to-date, relevant information. "
    "Describe the ideal page rather than listing keywords."
)

DEFAULT_GET_CONTENTS_DESCRIPTION = (
    "Read the full contents of web pages you already have URLs for, such as "
    "pages returned by a search or mentioned by the user."
)


class _WebSearchInput(BaseModel):
    query: str = Field(
        description=(
            "Natural language search query. Should be a semantically rich "
            "description of the ideal page, not just keywords."
        )
    )


class _GetContentsInput(BaseModel):
    urls: list[str] = Field(
        description=(
            "Absolute URLs of the pages to read, including the scheme. Pass "
            "several URLs to read them in a single call."
        )
    )


def _value(result: Any, name: str, default: Any = None) -> Any:
    if isinstance(result, Mapping):
        return result.get(name, default)
    return getattr(result, name, default)


def _format_results(response: Any, empty_message: str) -> str:
    results = _value(response, "results", []) or []
    formatted = []
    for result in results:
        lines = [
            f"Title: {_value(result, 'title') or 'N/A'}",
            f"URL: {_value(result, 'url') or 'N/A'}",
            f"Published: {_value(result, 'published_date') or 'N/A'}",
            f"Author: {_value(result, 'author') or 'N/A'}",
        ]
        summary = _value(result, "summary")
        highlights = _value(result, "highlights")
        text = _value(result, "text")
        if summary:
            lines.append(f"Summary: {summary}")
        if highlights:
            lines.append(f"Highlights:\n{chr(10).join(highlights)}")
        elif text:
            lines.append(f"Text: {text}")
        formatted.append("\n".join(lines))
    return "\n\n---\n\n".join(formatted) or empty_message


def _format_response(response: Any) -> str:
    return _format_results(response, "No search results found.")


def _format_contents_response(response: Any) -> str:
    return _format_results(response, "No contents found.")


def _schema(model: type[BaseModel]) -> dict[str, Any]:
    schema = model.model_json_schema()
    schema.pop("$schema", None)
    schema.pop("title", None)
    return schema


class _ToolSpec:
    def __init__(
        self,
        *,
        name: str,
        description: str,
        input_model: type[BaseModel],
        execute: Callable[[dict[str, Any]], Any],
        registry: "_ToolRegistry",
        formatter: Callable[[Any], str] = _format_response,
    ):
        self.name = name
        self.description = description
        self.input_model = input_model
        self.input_schema = _schema(input_model)
        self.json_schema = self.input_schema
        self._execute = execute
        self._formatter = formatter
        self.definition = {
            "name": name,
            "description": description,
            "parameters": self.input_schema,
        }
        registry.register(self)

    def execute(self, args: Any) -> Any:
        """Execute the underlying Exa request and return its raw response.

        Args:
            args: Tool arguments matching the input schema.

        Returns:
            The raw Exa response object.

        Examples:
            ``response = exa.tools.web_search().execute({"query": "AI"})``.
        """
        return self._execute(self.parse_args(args))

    def run(self, args: Any) -> str:
        """Execute and format a tool call for model consumption.

        Args:
            args: Tool arguments matching the input schema.

        Returns:
            Formatted output or a model-visible error string.

        Examples:
            ``text = exa.openai.web_search().run({"query": "AI"})``.
        """
        try:
            return self.format(self.execute(args))
        except Exception as error:
            return f"Error: {error}"

    def parse_args(self, args: Any) -> dict[str, Any]:
        """Validate and normalize tool arguments."""
        return self.input_model.model_validate(args).model_dump()

    def format(self, result: Any) -> str:
        return self._formatter(result)

    async def async_run(self, args: Any) -> str:
        """Execute a synchronous tool through an awaitable compatibility method.

        Args:
            args: Tool arguments matching the input schema.

        Returns:
            Formatted model-visible output.
        """
        return self.run(args)


class _AsyncToolSpec(_ToolSpec):
    def __init__(
        self,
        *,
        name: str,
        description: str,
        input_model: type[BaseModel],
        execute: Callable[[dict[str, Any]], Awaitable[Any]],
        registry: "_ToolRegistry",
        formatter: Callable[[Any], str] = _format_response,
    ):
        super().__init__(
            name=name,
            description=description,
            input_model=input_model,
            execute=execute,
            registry=registry,
            formatter=formatter,
        )

    async def execute(self, args: Any) -> Any:
        """Execute the underlying asynchronous Exa request.

        Args:
            args: Tool arguments matching the input schema.

        Returns:
            The raw Exa response object.
        """
        return await self._execute(self.parse_args(args))

    async def run(self, args: Any) -> str:
        """Execute and format an asynchronous tool call.

        Args:
            args: Tool arguments matching the input schema.

        Returns:
            Formatted output or a model-visible error string.
        """
        try:
            return self.format(await self.execute(args))
        except Exception as error:
            return f"Error: {error}"

    async def async_run(self, args: Any) -> str:
        """Alias for the asynchronous ``run`` method."""
        return await self.run(args)


class _ToolRegistry:
    def __init__(self):
        self._tools: dict[str, _ToolSpec] = {}

    def register(self, tool: _ToolSpec) -> None:
        self._tools[tool.name] = tool

    def resolve(self, tools: Optional[list[_ToolSpec]]) -> dict[str, _ToolSpec]:
        if tools is None:
            return dict(self._tools)
        resolved = {}
        for tool in tools:
            candidate = getattr(tool, "_exa_spec", None) or tool
            name = getattr(candidate, "name", None)
            if name is None:
                continue
            resolved[name] = candidate
        return resolved


class _OpenAIToolBase(dict):
    """A wire-safe OpenAI tool dictionary with an executable handle."""

    def __init__(self, definition: dict[str, Any], spec: _ToolSpec):
        super().__init__(definition)
        self.name = spec.name
        self.description = spec.description
        self.input_schema = spec.input_schema
        self.json_schema = spec.json_schema
        self._exa_spec = spec
        self.definition = dict(definition)

    def run(self, args: Any) -> Any:
        """Execute this tool and format the result.

        Args:
            args: Tool arguments matching the tool schema.

        Returns:
            Formatted model-visible output.
        """
        return self._exa_spec.run(args)

    def execute(self, args: Any) -> Any:
        """Execute this tool and return the raw Exa response.

        Args:
            args: Tool arguments matching the tool schema.

        Returns:
            The raw Exa response object.
        """
        return self._exa_spec.execute(args)

    def format(self, result: Any) -> str:
        """Format a raw Exa response for model consumption.

        Args:
            result: Raw Exa response.

        Returns:
            Formatted output.
        """
        return self._exa_spec.format(result)

    async def async_run(self, args: Any) -> str:
        """Execute this tool asynchronously and format the result.

        Args:
            args: Tool arguments matching the tool schema.

        Returns:
            Formatted model-visible output.
        """
        return await self._exa_spec.async_run(args)


class OpenAITool(_OpenAIToolBase):
    """A wire-safe OpenAI Chat Completions function tool."""


class OpenAIResponsesTool(_OpenAIToolBase):
    """A wire-safe OpenAI Responses function tool."""

class AsyncOpenAITool(_OpenAIToolBase):
    """A wire-safe OpenAI Chat Completions tool for ``AsyncExa``."""

    async def run(self, args: Any) -> str:
        """Execute this tool asynchronously.

        Args:
            args: Tool arguments matching the tool schema.

        Returns:
            Formatted model-visible output.
        """
        return await self._exa_spec.run(args)

    async def execute(self, args: Any) -> Any:
        """Execute this tool asynchronously and return the raw response.

        Args:
            args: Tool arguments matching the tool schema.

        Returns:
            The raw Exa response object.
        """
        return await self._exa_spec.execute(args)

    async def async_run(self, args: Any) -> str:
        """Alias for asynchronous ``run``."""
        return await self.run(args)


class AsyncOpenAIResponsesTool(AsyncOpenAITool):
    """A wire-safe OpenAI Responses tool for ``AsyncExa``."""


class ToolNamespace:
    def __init__(self, exa: Any, registry: _ToolRegistry):
        self._exa = exa
        self._registry = registry

    def web_search(self, **kwargs: Any) -> _ToolSpec:
        """Create a provider-neutral Exa search tool.

        Defaults to ``type="auto"`` and ``contents={"highlights": True}``.

        Args:
            **kwargs: Optional search options passed through to ``Exa.search``.
                ``name`` (default ``"web_search"``) and ``description`` override
                the advertised tool name and description instead; use a custom
                ``name`` to avoid clashes with other tools (e.g. Anthropic's
                built-in ``web_search`` tool).

        Returns:
            A registered executable tool specification.

        Examples:
            ``exa.tools.web_search()`` or ``exa.tools.web_search(name="exa_web_search")``.
        """
        return _create_web_search(self._exa, self._registry, False, kwargs)

    def get_contents(self, **kwargs: Any) -> _ToolSpec:
        """Create a provider-neutral Exa contents tool.

        Inherits ``Exa.get_contents`` defaults, which return page text capped at
        10,000 characters when no content option is configured.

        Args:
            **kwargs: Optional contents options passed through to
                ``Exa.get_contents`` (e.g. ``text``, ``summary``, ``livecrawl``).
                ``name`` (default ``"get_contents"``) and ``description``
                override the advertised tool name and description instead.

        Returns:
            A registered executable tool specification.

        Examples:
            ``exa.tools.get_contents()`` or ``exa.tools.get_contents(summary=True)``.
        """
        return _create_get_contents(self._exa, self._registry, False, kwargs)


class OpenAINamespace(ToolNamespace):
    def web_search(self, **kwargs: Any) -> OpenAITool:
        """Create an OpenAI Chat Completions web search tool.

        Defaults to ``type="auto"`` and ``contents={"highlights": True}``.

        Examples:
            ``tools=[exa.openai.web_search()]``.
        """
        spec = super().web_search(**kwargs)
        return _openai_tool(spec)

    def get_contents(self, **kwargs: Any) -> OpenAITool:
        """Create an OpenAI Chat Completions contents tool.

        Args:
            **kwargs: Contents options plus ``name`` and ``description``.

        Returns:
            A wire-safe OpenAI tool with an executable handle.

        Examples:
            ``tools=[exa.openai.get_contents()]``.
        """
        return _openai_tool(super().get_contents(**kwargs))

    def handle_tool_calls(
        self, message: Any, tools: Optional[list[_ToolSpec]] = None
    ) -> list[dict[str, Any]]:
        """Handle either Chat Completions or Responses tool calls.

        Args:
            message: A Chat Completions assistant message, Responses response,
                or Responses output-item list.
            tools: Optional explicit tools to resolve.

        Returns:
            Provider-specific tool result messages. Every tool call is
            answered: calls whose name matches no resolvable tool produce an
            ``Error: unknown tool "<name>"`` output so the follow-up request
            stays valid. Callers running mixed toolsets should replace these
            error outputs with their own results before the next request.
        """
        if _is_responses_input(message):
            return self.responses.handle_tool_calls(message, tools)
        return self._handle_chat_tool_calls(message, tools)

    def _handle_chat_tool_calls(
        self, assistant_message: Any, tools: Optional[list[_ToolSpec]] = None
    ) -> list[dict[str, str]]:
        """Convert OpenAI Chat Completions tool calls to tool messages.

        Args:
            assistant_message: The assistant message containing tool calls.
            tools: Optional explicit tools to resolve instead of this client's registry.

        Returns:
            Tool-role messages suitable for the next Chat Completions request.
            Calls naming an unresolvable tool get an ``Error: unknown tool
            "<name>"`` message instead of being dropped.
        """
        registry = self._registry.resolve(tools)
        calls = _value(assistant_message, "tool_calls", []) or []
        messages = []
        for call in calls:
            function = _value(call, "function", {})
            name = _value(function, "name")
            tool = registry.get(name)
            if tool is None:
                content = f'Error: unknown tool "{name}"'
            else:
                content = tool.run(_json_loads(_value(function, "arguments", "")))
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": _value(call, "id"),
                    "content": content,
                }
            )
        return messages

    async def handle_tool_calls_async(
        self, assistant_message: Any, tools: Optional[list[_ToolSpec]] = None
    ) -> list[dict[str, str]]:
        registry = self._registry.resolve(tools)
        calls = _value(assistant_message, "tool_calls", []) or []

        async def handle(call: Any) -> dict[str, str]:
            function = _value(call, "function", {})
            name = _value(function, "name")
            tool = registry.get(name)
            if tool is None:
                content = f'Error: unknown tool "{name}"'
            else:
                content = await tool.async_run(
                    _json_loads(_value(function, "arguments", ""))
                )
            return {
                "role": "tool",
                "tool_call_id": _value(call, "id"),
                "content": content,
            }

        results = await _gather(*(handle(call) for call in calls))
        return [result for result in results if result is not None]

    @property
    def responses(self) -> "OpenAIResponsesNamespace":
        return OpenAIResponsesNamespace(self._exa, self._registry)


class OpenAIResponsesNamespace(ToolNamespace):
    def web_search(self, **kwargs: Any) -> OpenAIResponsesTool:
        return _responses_tool(super().web_search(**kwargs))

    def get_contents(self, **kwargs: Any) -> OpenAIResponsesTool:
        """Create an OpenAI Responses contents tool.

        Args:
            **kwargs: Contents options plus ``name`` and ``description``.

        Returns:
            A wire-safe OpenAI Responses tool with an executable handle.

        Examples:
            ``tools=[exa.openai.responses.get_contents()]``.
        """
        return _responses_tool(super().get_contents(**kwargs))

    def handle_tool_calls(
        self, response_or_items: Any, tools: Optional[list[_ToolSpec]] = None
    ) -> list[dict[str, str]]:
        """Convert OpenAI Responses function calls to output items.

        Args:
            response_or_items: A Responses response or its output item list.
            tools: Optional explicit tools to resolve instead of this client's registry.

        Returns:
            ``function_call_output`` items for a follow-up Responses request.
            Every function call is answered: calls naming an unresolvable tool
            get an ``Error: unknown tool "<name>"`` output instead of being
            dropped. Callers running mixed toolsets should replace these error
            outputs with their own results before the next request.
        """
        registry = self._registry.resolve(tools)
        items = (
            _value(response_or_items, "output", [])
            if hasattr(response_or_items, "output")
            or isinstance(response_or_items, Mapping)
            else response_or_items
        )
        outputs = []
        for item in items or []:
            if _value(item, "type") != "function_call":
                continue
            name = _value(item, "name")
            tool = registry.get(name)
            if tool is None:
                output = f'Error: unknown tool "{name}"'
            else:
                output = tool.run(_json_loads(_value(item, "arguments", "")))
            outputs.append(
                {
                    "type": "function_call_output",
                    "call_id": _value(item, "call_id"),
                    "output": output,
                }
            )
        return outputs

    async def handle_tool_calls_async(
        self, response_or_items: Any, tools: Optional[list[_ToolSpec]] = None
    ) -> list[dict[str, str]]:
        registry = self._registry.resolve(tools)
        items = (
            _value(response_or_items, "output", [])
            if hasattr(response_or_items, "output")
            or isinstance(response_or_items, Mapping)
            else response_or_items
        )

        async def handle(item: Any) -> Optional[dict[str, str]]:
            if _value(item, "type") != "function_call":
                return None
            name = _value(item, "name")
            tool = registry.get(name)
            if tool is None:
                output = f'Error: unknown tool "{name}"'
            else:
                output = await tool.async_run(
                    _json_loads(_value(item, "arguments", ""))
                )
            return {
                "type": "function_call_output",
                "call_id": _value(item, "call_id"),
                "output": output,
            }

        results = await _gather(*(handle(item) for item in items or []))
        return [result for result in results if result is not None]


class AnthropicNamespace(ToolNamespace):
    def web_search(self, **kwargs: Any) -> Any:
        return _anthropic_tool(super().web_search(**kwargs), False)

    def get_contents(self, **kwargs: Any) -> Any:
        """Create an Anthropic Messages contents tool.

        Args:
            **kwargs: Contents options plus ``name`` and ``description``.

        Returns:
            A wire-safe Anthropic tool with an executable handle.

        Examples:
            ``tools=[exa.anthropic.get_contents()]``.
        """
        return _anthropic_tool(super().get_contents(**kwargs), False)

    def handle_tool_use(
        self, message: Any, tools: Optional[list[_ToolSpec]] = None
    ) -> list[dict[str, Any]]:
        """Convert Anthropic tool-use blocks to tool-result blocks.

        Args:
            message: An Anthropic message containing tool-use blocks.
            tools: Optional explicit tools to resolve instead of this client's registry.

        Returns:
            Tool-result content blocks for the next Messages request. Every
            tool-use block is answered: blocks naming an unresolvable tool get
            an ``Error: unknown tool "<name>"`` result instead of being
            dropped. Callers running mixed toolsets should replace these error
            outputs with their own results before the next request.
        """
        registry = self._registry.resolve(tools)
        results = []
        for block in _value(message, "content", []) or []:
            if _value(block, "type") != "tool_use":
                continue
            name = _value(block, "name")
            tool = registry.get(name)
            if tool is None:
                content = f'Error: unknown tool "{name}"'
            else:
                content = tool.run(_value(block, "input"))
            results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": _value(block, "id"),
                    "content": content,
                }
            )
        return results

    async def handle_tool_use_async(
        self, message: Any, tools: Optional[list[_ToolSpec]] = None
    ) -> list[dict[str, Any]]:
        registry = self._registry.resolve(tools)
        blocks = [
            block
            for block in (_value(message, "content", []) or [])
            if _value(block, "type") == "tool_use"
        ]

        async def handle(block: Any) -> dict[str, Any]:
            name = _value(block, "name")
            tool = registry.get(name)
            if tool is None:
                content = f'Error: unknown tool "{name}"'
            else:
                content = await tool.async_run(_value(block, "input"))
            return {
                "type": "tool_result",
                "tool_use_id": _value(block, "id"),
                "content": content,
            }

        results = await _gather(*(handle(block) for block in blocks))
        return [result for result in results if result is not None]


class AsyncToolNamespace(ToolNamespace):
    """Provider-neutral tool namespace for ``AsyncExa``."""

    def web_search(self, **kwargs: Any) -> _AsyncToolSpec:
        """Create an asynchronous provider-neutral search tool.

        Args:
            **kwargs: Search options and tool options.

        Returns:
            An asynchronous executable tool specification.

        Examples:
            ``tool = async_exa.tools.web_search()``.
        """
        return _create_web_search(self._exa, self._registry, True, kwargs)

    def get_contents(self, **kwargs: Any) -> _AsyncToolSpec:
        """Create an asynchronous provider-neutral contents tool.

        Args:
            **kwargs: Contents options and tool options.

        Returns:
            An asynchronous executable tool specification.

        Examples:
            ``tool = async_exa.tools.get_contents()``.
        """
        return _create_get_contents(self._exa, self._registry, True, kwargs)


class AsyncOpenAINamespace(OpenAINamespace, AsyncToolNamespace):
    """OpenAI tool namespace for ``AsyncExa``."""

    def web_search(self, **kwargs: Any) -> AsyncOpenAITool:
        return _openai_tool(
            _create_web_search(self._exa, self._registry, True, kwargs), asynchronous=True
        )

    def get_contents(self, **kwargs: Any) -> AsyncOpenAITool:
        return _openai_tool(
            _create_get_contents(self._exa, self._registry, True, kwargs),
            asynchronous=True,
        )

    async def handle_tool_calls(
        self, message: Any, tools: Optional[list[_ToolSpec]] = None
    ) -> list[dict[str, Any]]:
        """Asynchronously convert Chat Completions tool calls to tool messages.

        Args:
            assistant_message: The assistant message containing tool calls.
            tools: Optional explicit tools to resolve.

        Returns:
            Tool-role messages for a follow-up request. Calls naming an
            unresolvable tool get an ``Error: unknown tool "<name>"`` message
            instead of being dropped. Callers running mixed toolsets should
            replace these error outputs with their own results before the next
            request.
        """
        if _is_responses_input(message):
            return await self.responses.handle_tool_calls(message, tools)
        return await self.handle_tool_calls_async(message, tools)

    @property
    def responses(self) -> "AsyncOpenAIResponsesNamespace":
        return AsyncOpenAIResponsesNamespace(self._exa, self._registry)


class AsyncOpenAIResponsesNamespace(OpenAIResponsesNamespace, AsyncToolNamespace):
    """OpenAI Responses tool namespace for ``AsyncExa``."""

    def web_search(self, **kwargs: Any) -> AsyncOpenAIResponsesTool:
        return _responses_tool(
            _create_web_search(self._exa, self._registry, True, kwargs),
            asynchronous=True,
        )

    def get_contents(self, **kwargs: Any) -> AsyncOpenAIResponsesTool:
        return _responses_tool(
            _create_get_contents(self._exa, self._registry, True, kwargs),
            asynchronous=True,
        )

    async def handle_tool_calls(
        self, response_or_items: Any, tools: Optional[list[_ToolSpec]] = None
    ) -> list[dict[str, str]]:
        """Asynchronously convert Responses function calls to output items.

        Args:
            response_or_items: A Responses response or output item list.
            tools: Optional explicit tools to resolve.

        Returns:
            ``function_call_output`` items for a follow-up request. Calls
            naming an unresolvable tool get an ``Error: unknown tool
            "<name>"`` output instead of being dropped. Callers running mixed
            toolsets should replace these error outputs with their own results
            before the next request.
        """
        return await self.handle_tool_calls_async(response_or_items, tools)


class AsyncAnthropicNamespace(AnthropicNamespace, AsyncToolNamespace):
    """Anthropic tool namespace for ``AsyncExa``."""

    def web_search(self, **kwargs: Any) -> Any:
        return _anthropic_tool(
            _create_web_search(self._exa, self._registry, True, kwargs), True
        )

    def get_contents(self, **kwargs: Any) -> Any:
        return _anthropic_tool(
            _create_get_contents(self._exa, self._registry, True, kwargs), True
        )

    async def handle_tool_use(
        self, message: Any, tools: Optional[list[_ToolSpec]] = None
    ) -> list[dict[str, Any]]:
        """Asynchronously convert Anthropic tool-use blocks to results.

        Args:
            message: An Anthropic message containing tool-use blocks.
            tools: Optional explicit tools to resolve.

        Returns:
            ``tool_result`` blocks for a follow-up request. Blocks naming an
            unresolvable tool get an ``Error: unknown tool "<name>"`` result
            instead of being dropped. Callers running mixed toolsets should
            replace these error outputs with their own results before the next
            request.
        """
        return await self.handle_tool_use_async(message, tools)


def _create_web_search(
    exa: Any, registry: _ToolRegistry, asynchronous: bool, kwargs: dict[str, Any]
) -> _ToolSpec:
    config = dict(kwargs)
    name = config.pop("name", "web_search")
    description = config.pop("description", DEFAULT_WEB_SEARCH_DESCRIPTION)
    search_type = config.pop("type", "auto")
    search_num_results = config.pop("num_results", 10)
    search_contents = config.pop("contents", {"highlights": True})

    def execute(args: dict[str, Any]) -> Any:
        return exa.search(
            args["query"],
            type=search_type,
            num_results=search_num_results,
            contents=search_contents,
            **config,
        )

    async def async_execute(args: dict[str, Any]) -> Any:
        return await exa.search(
            args["query"],
            type=search_type,
            num_results=search_num_results,
            contents=search_contents,
            **config,
        )

    spec_class = _AsyncToolSpec if asynchronous else _ToolSpec
    spec = spec_class(
        name=name,
        description=description,
        input_model=_WebSearchInput,
        execute=async_execute if asynchronous else execute,
        registry=registry,
    )
    return spec


def _create_get_contents(
    exa: Any, registry: _ToolRegistry, asynchronous: bool, kwargs: dict[str, Any]
) -> _ToolSpec:
    config = dict(kwargs)
    name = config.pop("name", "get_contents")
    description = config.pop("description", DEFAULT_GET_CONTENTS_DESCRIPTION)

    def execute(args: dict[str, Any]) -> Any:
        return exa.get_contents(args["urls"], **config)

    async def async_execute(args: dict[str, Any]) -> Any:
        return await exa.get_contents(args["urls"], **config)

    spec_class = _AsyncToolSpec if asynchronous else _ToolSpec
    return spec_class(
        name=name,
        description=description,
        input_model=_GetContentsInput,
        execute=async_execute if asynchronous else execute,
        registry=registry,
        formatter=_format_contents_response,
    )


def _openai_tool(spec: _ToolSpec, asynchronous: bool = False) -> OpenAITool:
    tool_class = AsyncOpenAITool if asynchronous else OpenAITool
    return tool_class(
        {
            "type": "function",
            "function": {
                "name": spec.name,
                "description": spec.description,
                "parameters": spec.json_schema,
            },
        },
        spec,
    )


def _responses_tool(
    spec: _ToolSpec, asynchronous: bool = False
) -> OpenAIResponsesTool:
    tool_class = AsyncOpenAIResponsesTool if asynchronous else OpenAIResponsesTool
    return tool_class(
        {
            "type": "function",
            "name": spec.name,
            "description": spec.description,
            "parameters": spec.json_schema,
            "strict": False,
        },
        spec,
    )


class _AnthropicToolBase(dict):
    """A wire-safe Anthropic tool dictionary with an executable handle."""

    def __init__(self, spec: _ToolSpec):
        super().__init__(
            {
                "name": spec.name,
                "description": spec.description,
                "input_schema": spec.json_schema,
            }
        )
        self.name = spec.name
        self.description = spec.description
        self.input_schema = spec.input_schema
        self.json_schema = spec.json_schema
        self._exa_spec = spec
        self.definition = dict(self)

    def run(self, args: Any) -> Any:
        """Execute this tool and format the result."""
        return self._exa_spec.run(args)

    def execute(self, args: Any) -> Any:
        """Execute this tool and return the raw Exa response."""
        return self._exa_spec.execute(args)

    def format(self, result: Any) -> str:
        """Format a raw Exa response for model consumption."""
        return self._exa_spec.format(result)


class _AsyncAnthropicTool(_AnthropicToolBase):
    """An asynchronous wire-safe Anthropic tool dictionary."""

    async def run(self, args: Any) -> str:
        """Execute this tool asynchronously and format the result."""
        return await self._exa_spec.run(args)

    async def execute(self, args: Any) -> Any:
        """Execute this tool asynchronously and return the raw response."""
        return await self._exa_spec.execute(args)

    async def async_run(self, args: Any) -> str:
        """Alias for asynchronous ``run``."""
        return await self.run(args)


def _anthropic_tool(spec: _ToolSpec, asynchronous: bool) -> _AnthropicToolBase:
    return (_AsyncAnthropicTool if asynchronous else _AnthropicToolBase)(spec)


def _json_loads(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def _is_responses_input(value: Any) -> bool:
    if isinstance(value, Mapping):
        if "output" in value:
            return True
        items = value.get("output")
    elif hasattr(value, "output"):
        return True
    else:
        items = value if isinstance(value, list) else None
    return any(_value(item, "type") == "function_call" for item in items or [])


ToolSpec = _ToolSpec


async def _gather(*awaitables: Awaitable[Optional[dict[str, Any]]]) -> list[Any]:
    return list(await asyncio.gather(*awaitables))
