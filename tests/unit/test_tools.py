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
        summary=kwargs.get("summary"),
    )


def test_openai_tool_is_wire_safe_and_has_query_only_schema(monkeypatch):
    exa = Exa("test")
    exa.search = lambda query, **kwargs: response(result(highlights=["A fact"]))
    tool = exa.openai.web_search()

    assert list(tool) == ["type", "function"]
    assert json.loads(json.dumps(tool)) == tool
    assert tool["function"]["parameters"]["required"] == ["query"]
    assert "$schema" not in tool["function"]["parameters"]
    assert "title" not in tool["function"]["parameters"]
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
    exa.openai.web_search(num_results=4, type="auto").run({"query": "q"})
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
    tool = exa.openai.web_search(
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
    tool = exa.tools.web_search()
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
    tool = exa.openai.web_search()
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
        {"role": "tool", "tool_call_id": "3", "content": 'Error: unknown tool "other"'},
    ]
    assert calls == ["a", "b"]
    assert exa.openai.handle_tool_calls(message, tools=[]) == [
        {"role": "tool", "tool_call_id": "1", "content": 'Error: unknown tool "web_search"'},
        {"role": "tool", "tool_call_id": "2", "content": 'Error: unknown tool "web_search"'},
        {"role": "tool", "tool_call_id": "3", "content": 'Error: unknown tool "other"'},
    ]
    assert tool.name == "web_search"

    mixed = exa.openai.handle_tool_calls(
        message,
        tools=[tool, {"type": "function", "function": {"name": "other"}}],
    )
    assert [m["tool_call_id"] for m in mixed] == ["1", "2", "3"]
    assert "Highlights" in mixed[0]["content"]
    assert mixed[2]["content"] == 'Error: unknown tool "other"'


def test_custom_name_and_description_propagate():
    exa = Exa("test")
    exa.search = lambda query, **kwargs: response(result(highlights=["custom hit"]))

    chat_tool = exa.openai.web_search(name="exa_web_search", description="Exa search")
    assert chat_tool["function"]["name"] == "exa_web_search"
    assert chat_tool["function"]["description"] == "Exa search"
    assert chat_tool.name == "exa_web_search"
    assert chat_tool.description == "Exa search"
    assert chat_tool._exa_spec.definition["name"] == "exa_web_search"
    assert chat_tool._exa_spec.definition["description"] == "Exa search"

    responses_tool = exa.openai.responses.web_search(
        name="exa_web_search", description="Exa search"
    )
    assert responses_tool["name"] == "exa_web_search"
    assert responses_tool["description"] == "Exa search"

    anthropic_tool = exa.anthropic.web_search(name="exa_web_search", description="Exa search")
    assert anthropic_tool == {
        "name": "exa_web_search",
        "description": "Exa search",
        "input_schema": anthropic_tool.json_schema,
    }

    default_tool = exa.openai.web_search()
    assert default_tool["function"]["name"] == "web_search"

    outputs = exa.openai.handle_tool_calls(
        {
            "tool_calls": [
                {"id": "1", "function": {"name": "exa_web_search", "arguments": '{"query":"q"}'}},
                {"id": "2", "function": {"name": "web_search", "arguments": '{"query":"q"}'}},
            ]
        }
    )
    assert all("custom hit" in output["content"] for output in outputs)
    assert [output["tool_call_id"] for output in outputs] == ["1", "2"]

    responses_outputs = exa.openai.responses.handle_tool_calls(
        [
            {
                "type": "function_call",
                "name": "exa_web_search",
                "call_id": "c",
                "arguments": '{"query":"q"}',
            }
        ]
    )
    assert "custom hit" in responses_outputs[0]["output"]

    anthropic_outputs = exa.anthropic.handle_tool_use(
        {"content": [{"type": "tool_use", "id": "u", "name": "exa_web_search", "input": {"query": "q"}}]}
    )
    assert "custom hit" in anthropic_outputs[0]["content"]


def test_custom_name_and_description_not_passed_to_search():
    exa = Exa("test")
    seen = {}

    def search(query, **kwargs):
        seen["query"] = query
        seen["kwargs"] = kwargs
        return response(result(highlights=["x"]))

    exa.search = search
    tool = exa.anthropic.web_search(
        name="exa_web_search",
        description="Exa search",
        num_results=3,
        category="news",
    )
    tool.run({"query": "q"})
    assert seen["query"] == "q"
    assert seen["kwargs"] == {
        "type": "auto",
        "num_results": 3,
        "contents": {"highlights": True},
        "category": "news",
    }


def test_differently_named_tools_coexist():
    exa = Exa("test")
    requests = []

    def search(query, **kwargs):
        requests.append((query, kwargs))
        return response(result(highlights=[query]))

    exa.search = search
    exa.openai.web_search()
    exa.openai.web_search(name="news_search", category="news", num_results=3)

    outputs = exa.openai.handle_tool_calls(
        {
            "tool_calls": [
                {"id": "1", "function": {"name": "web_search", "arguments": '{"query":"a"}'}},
                {"id": "2", "function": {"name": "news_search", "arguments": '{"query":"b"}'}},
            ]
        }
    )
    assert [output["tool_call_id"] for output in outputs] == ["1", "2"]
    assert requests == [
        ("a", {"type": "auto", "num_results": 10, "contents": {"highlights": True}}),
        (
            "b",
            {
                "type": "auto",
                "num_results": 3,
                "contents": {"highlights": True},
                "category": "news",
            },
        ),
    ]


def test_unknown_tool_calls_produce_error_outputs():
    exa = Exa("test")
    exa.search = lambda query, **kwargs: response(result(highlights=["ok"]))
    exa.openai.web_search()

    chat_outputs = exa.openai.handle_tool_calls(
        {"tool_calls": [{"id": "1", "function": {"name": "missing", "arguments": "{}"}}]}
    )
    assert chat_outputs == [
        {"role": "tool", "tool_call_id": "1", "content": 'Error: unknown tool "missing"'}
    ]

    responses_outputs = exa.openai.responses.handle_tool_calls(
        [{"type": "function_call", "name": "missing", "call_id": "c", "arguments": "{}"}]
    )
    assert responses_outputs == [
        {
            "type": "function_call_output",
            "call_id": "c",
            "output": 'Error: unknown tool "missing"',
        }
    ]

    anthropic_outputs = exa.anthropic.handle_tool_use(
        {"content": [{"type": "tool_use", "id": "u", "name": "missing", "input": {}}]}
    )
    assert anthropic_outputs == [
        {
            "type": "tool_result",
            "tool_use_id": "u",
            "content": 'Error: unknown tool "missing"',
        }
    ]


def test_responses_and_anthropic_tools():
    exa = Exa("test")
    exa.search = lambda query, **kwargs: response(result(highlights=["ok"]))
    responses_tool = exa.openai.responses.web_search()
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

    anthropic_tool = exa.anthropic.web_search()
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
    tool = exa.openai.web_search()
    assert isinstance(tool, dict)
    assert await tool.run({"query": "q"})
    outputs = await exa.openai.handle_tool_calls(
        {
            "tool_calls": [
                {"id": "1", "function": {"name": "web_search", "arguments": '{"query":"q"}'}},
                {"id": "2", "function": {"name": "missing", "arguments": "{}"}},
            ]
        }
    )
    assert outputs[0]["tool_call_id"] == "1"
    assert outputs[1] == {
        "role": "tool",
        "tool_call_id": "2",
        "content": 'Error: unknown tool "missing"',
    }

    responses_outputs = await exa.openai.responses.handle_tool_calls(
        [{"type": "function_call", "name": "missing", "call_id": "c", "arguments": "{}"}]
    )
    assert responses_outputs == [
        {
            "type": "function_call_output",
            "call_id": "c",
            "output": 'Error: unknown tool "missing"',
        }
    ]

    anthropic_tool = exa.anthropic.web_search()
    assert anthropic_tool["name"] == "web_search"
    outputs = await exa.anthropic.handle_tool_use(
        {
            "content": [
                {"type": "tool_use", "id": "u", "name": "web_search", "input": {"query": "q"}},
                {"type": "tool_use", "id": "v", "name": "missing", "input": {}},
            ]
        }
    )
    assert outputs[0]["tool_use_id"] == "u"
    assert outputs[1] == {
        "type": "tool_result",
        "tool_use_id": "v",
        "content": 'Error: unknown tool "missing"',
    }


def test_contents_tool_is_wire_safe_and_takes_urls():
    exa = Exa("test")
    exa.get_contents = lambda urls, **kwargs: response(result(text="Page text"))
    tool = exa.openai.get_contents()

    assert list(tool) == ["type", "function"]
    assert json.loads(json.dumps(tool)) == tool
    assert tool["function"]["name"] == "get_contents"
    assert tool["function"]["parameters"]["required"] == ["urls"]
    assert set(tool["function"]["parameters"]["properties"]) == {"urls"}
    assert tool["function"]["parameters"]["properties"]["urls"]["type"] == "array"
    assert "$schema" not in tool["function"]["parameters"]
    assert "run" not in json.dumps(tool)
    assert "Text: Page text" in tool.run({"urls": ["https://example.com"]})


def test_contents_passes_urls_and_options_through():
    exa = Exa("test")
    seen = {}

    def get_contents(urls, **kwargs):
        seen["urls"] = urls
        seen["kwargs"] = kwargs
        return response(result(summary="A summary"))

    exa.get_contents = get_contents
    tool = exa.tools.get_contents(
        name="read_pages",
        description="Read pages",
        summary=True,
        livecrawl="preferred",
    )
    output = tool.run({"urls": ["https://example.com", "https://exa.ai"]})

    assert seen["urls"] == ["https://example.com", "https://exa.ai"]
    assert seen["kwargs"] == {"summary": True, "livecrawl": "preferred"}
    assert "Summary: A summary" in output
    assert tool.name == "read_pages"
    assert tool.description == "Read pages"


def test_contents_reports_empty_and_failed_results():
    exa = Exa("test")
    exa.get_contents = lambda urls, **kwargs: response()
    tool = exa.tools.get_contents()
    assert tool.run({"urls": ["https://example.com"]}) == "No contents found."
    assert "Error:" in tool.run({"urls": "not-a-list"})

    exa.get_contents = lambda urls, **kwargs: (_ for _ in ()).throw(
        ValueError("upstream")
    )
    assert tool.run({"urls": ["https://example.com"]}) == "Error: upstream"


def test_contents_and_search_tools_coexist_across_providers():
    exa = Exa("test")
    exa.search = lambda query, **kwargs: response(result(highlights=["a fact"]))
    exa.get_contents = lambda urls, **kwargs: response(result(text="Page text"))
    exa.openai.web_search()
    exa.openai.get_contents()

    outputs = exa.openai.handle_tool_calls(
        {
            "tool_calls": [
                {"id": "1", "function": {"name": "web_search", "arguments": '{"query":"q"}'}},
                {
                    "id": "2",
                    "function": {
                        "name": "get_contents",
                        "arguments": '{"urls":["https://example.com"]}',
                    },
                },
            ]
        }
    )
    assert "a fact" in outputs[0]["content"]
    assert "Text: Page text" in outputs[1]["content"]

    responses_tool = exa.openai.responses.get_contents()
    assert responses_tool["type"] == "function"
    assert responses_tool["name"] == "get_contents"
    assert responses_tool.definition == dict(responses_tool)

    anthropic_tool = exa.anthropic.get_contents()
    assert anthropic_tool == {
        "name": "get_contents",
        "description": anthropic_tool.description,
        "input_schema": anthropic_tool.json_schema,
    }
    tool_results = exa.anthropic.handle_tool_use(
        {
            "content": [
                {
                    "type": "tool_use",
                    "id": "u",
                    "name": "get_contents",
                    "input": {"urls": ["https://example.com"]},
                }
            ]
        }
    )
    assert "Text: Page text" in tool_results[0]["content"]


@pytest.mark.asyncio
async def test_async_contents_tools_and_handlers():
    exa = AsyncExa("test")
    seen = {}

    async def get_contents(urls, **kwargs):
        seen["urls"] = urls
        return response(result(text="Page text"))

    exa.get_contents = get_contents
    tool = exa.openai.get_contents()
    assert "Text: Page text" in await tool.run({"urls": ["https://example.com"]})
    assert seen["urls"] == ["https://example.com"]

    outputs = await exa.openai.handle_tool_calls(
        {
            "tool_calls": [
                {
                    "id": "1",
                    "function": {
                        "name": "get_contents",
                        "arguments": '{"urls":["https://example.com"]}',
                    },
                }
            ]
        }
    )
    assert "Text: Page text" in outputs[0]["content"]

    responses_outputs = await exa.openai.responses.handle_tool_calls(
        [
            {
                "type": "function_call",
                "name": "get_contents",
                "call_id": "c",
                "arguments": '{"urls":["https://example.com"]}',
            }
        ]
    )
    assert "Text: Page text" in responses_outputs[0]["output"]

    anthropic_tool = exa.anthropic.get_contents()
    assert anthropic_tool["name"] == "get_contents"
    tool_results = await exa.anthropic.handle_tool_use(
        {
            "content": [
                {
                    "type": "tool_use",
                    "id": "u",
                    "name": "get_contents",
                    "input": {"urls": ["https://example.com"]},
                }
            ]
        }
    )
    assert "Text: Page text" in tool_results[0]["content"]
