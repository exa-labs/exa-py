import asyncio
import json
from types import SimpleNamespace

import pytest

from exa_py import AsyncExa, Exa


def response(*results):
    return SimpleNamespace(results=list(results))


def result(**kwargs):
    return SimpleNamespace(
        title=kwargs.get("title", "Example"),
        url=kwargs.get("url", "https://example.com"),
        published_date=kwargs.get("published_date"),
        author=kwargs.get("author"),
        highlights=kwargs.get("highlights"),
        text=kwargs.get("text"),
    )


def test_openai_tool_is_wire_safe_and_has_query_only_schema(monkeypatch):
    exa = Exa("test")
    exa.search = lambda query, **kwargs: response(result(highlights=["A fact"]))
    tool = exa.openai.search()

    assert list(tool) == ["type", "function"]
    assert json.loads(json.dumps(tool)) == tool
    assert tool["function"]["parameters"]["required"] == ["query"]
    assert "$schema" not in tool["function"]["parameters"]
    assert set(tool["function"]["parameters"]["properties"]) == {"query"}
    assert "run" not in json.dumps(tool)
    assert "A fact" in tool.run({"query": "news"})


def test_search_defaults_and_configured_options(monkeypatch):
    exa = Exa("test")
    seen = {}

    def search(query, **kwargs):
        seen.update(kwargs)
        return response(result(highlights=["x"]))

    exa.search = search
    exa.openai.search(num_results=4, type="auto").run({"query": "q"})
    assert seen["num_results"] == 4
    assert seen["type"] == "auto"
    assert seen["contents"] == {"highlights": True}


def test_explicit_content_limits():
    exa = Exa("test")
    seen = {}

    def search(query, **kwargs):
        seen.update(kwargs)
        return response(result(highlights=["x"]))

    exa.search = search
    tool = exa.openai.search(
        num_results=2,
        contents={"highlights": {"max_characters": 5000}},
    )
    tool.run({"query": "q"})
    assert seen["contents"]["highlights"]["max_characters"] == 5000


def test_model_visible_errors():
    exa = Exa("test")
    exa.search = lambda query, **kwargs: response(
        result(title="Long", highlights=["x" * 200])
    )
    tool = exa.tools.search()
    assert "x" * 200 in tool.run({"query": "q"})
    assert tool.execute({"query": "q"}).results[0].title == "Long"

    assert "Error:" in tool.run("bad")

    exa.search = lambda query, **kwargs: (_ for _ in ()).throw(ValueError("upstream"))
    assert tool.run({"query": "q"}) == "Error: upstream"


def test_handlers_parallel_calls_and_unknown_tools():
    exa = Exa("test")
    calls = []

    def search(query, **kwargs):
        calls.append(query)
        return response(result(highlights=[query]))

    exa.search = search
    tool = exa.openai.search()
    message = {
        "tool_calls": [
            {"id": "1", "function": {"name": "web_search", "arguments": '{"query":"a"}'}},
            {"id": "2", "function": {"name": "web_search", "arguments": '{"query":"b"}'}},
            {"id": "3", "function": {"name": "other", "arguments": "{}"}},
        ]
    }
    outputs = exa.openai.handle_tool_calls(message)
    assert outputs == [
        {"role": "tool", "tool_call_id": "1", "content": "Title: Example\nURL: https://example.com\nPublished: N/A\nAuthor: N/A\nHighlights:\na"},
        {"role": "tool", "tool_call_id": "2", "content": "Title: Example\nURL: https://example.com\nPublished: N/A\nAuthor: N/A\nHighlights:\nb"},
    ]
    assert calls == ["a", "b"]
    assert exa.openai.handle_tool_calls(message, tools=[]) == []
    assert tool.name == "web_search"


def test_responses_and_anthropic_tools():
    exa = Exa("test")
    exa.search = lambda query, **kwargs: response(result(highlights=["ok"]))
    responses_tool = exa.openai.responses.search()
    assert responses_tool["type"] == "function"
    assert responses_tool.definition == dict(responses_tool)
    assert "$schema" not in responses_tool["parameters"]
    response_items = [
        {
            "type": "function_call",
            "name": "web_search",
            "call_id": "c",
            "arguments": '{"query":"q"}',
        }
    ]
    output = exa.openai.handle_tool_calls(response_items)
    assert output[0]["type"] == "function_call_output"
    assert exa.openai.responses.handle_tool_calls(response_items) == output

    anthropic_tool = exa.anthropic.search()
    assert anthropic_tool == {
        "name": "web_search",
        "description": anthropic_tool.description,
        "input_schema": anthropic_tool.json_schema,
    }
    assert "$schema" not in anthropic_tool["input_schema"]
    tool_results = exa.anthropic.handle_tool_use(
        {"content": [{"type": "tool_use", "id": "u", "name": "web_search", "input": {"query": "q"}}]}
    )
    assert tool_results[0]["type"] == "tool_result"


@pytest.mark.asyncio
async def test_async_tools_and_handlers():
    exa = AsyncExa("test")

    async def search(query, **kwargs):
        return response(result(highlights=[query]))

    exa.search = search
    tool = exa.openai.search()
    assert isinstance(tool, dict)
    assert await tool.run({"query": "q"})
    outputs = await exa.openai.handle_tool_calls(
        {"tool_calls": [{"id": "1", "function": {"name": "web_search", "arguments": '{"query":"q"}'}}]}
    )
    assert outputs[0]["tool_call_id"] == "1"

    anthropic_tool = exa.anthropic.search()
    assert anthropic_tool["name"] == "web_search"
    outputs = await exa.anthropic.handle_tool_use(
        {"content": [{"type": "tool_use", "id": "u", "name": "web_search", "input": {"query": "q"}}]}
    )
    assert outputs[0]["tool_use_id"] == "u"
