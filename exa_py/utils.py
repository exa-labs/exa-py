import json
from typing import Any, Callable
from openai import OpenAI


from exa_py.api import SearchResponse


def maybe_get_query(completion) -> str | None:
    """Extract query from completion if it exists."""
    if completion.choices[0].message.tool_calls:
        print("Tool call detected.", completion.choices[0].message.tool_calls)
        for tool_call in completion.choices[0].message.tool_calls:
            if tool_call.function.name == "search":
                query = json.loads(tool_call.function.arguments)["query"]
                return query
    return None


def add_message_to_messages(completion, messages, exa_result) -> list[dict]:
    """Add assistant message and exa result to messages list. Also remove previous exa call and results."""
    assistant_message = completion.choices[0].message
    assert assistant_message.tool_calls, "Must use this with a tool call request"
    # Remove previous exa call and results to prevent blowing up history
    messages = [
        message
        for message in messages
        if not (message.get("role") == "function")
    ]
    
    messages.extend([
        assistant_message,
        {
            "role": "tool",
            "name": "search",
            "tool_call_id": assistant_message.tool_calls[0].id,
            "content": exa_result,
        }
    ])

    return messages


def format_exa_result(exa_result: SearchResponse, max_len: int=-1):
    """Format exa result for pasting into chat."""
    print("Formatting exa result")
    str = [
        f"Url: {result.url}\nTitle: {result.title}\n{result.text[:max_len]}\n"
        for result in exa_result.results
    ]

    return "\n".join(str)

