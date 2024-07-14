import json
from typing import Optional
from openai.types.chat import ChatCompletion

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from exa_py.api import ResultWithText, SearchResponse



def maybe_get_query(completion) -> Optional[str]:
    """Extract query from completion if it exists."""
    if completion.choices[0].message.tool_calls:
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


def format_exa_result(exa_result, max_len: int=-1):
    """Format exa result for pasting into chat."""
    str = [
        f"Url: {result.url}\nTitle: {result.title}\n{result.text[:max_len]}\n"
        for result in exa_result.results
    ]

    return "\n".join(str)


class ExaOpenAICompletion(ChatCompletion):
    """Exa wrapper for OpenAI completion."""
    def __init__(self, exa_result: Optional["SearchResponse[ResultWithText]"], **kwargs):
        super().__init__(**kwargs)
        self.exa_result = exa_result
    

    @classmethod
    def from_completion(
        cls, 
        exa_result: Optional["SearchResponse[ResultWithText]"], 
        completion: ChatCompletion
    ):

        return cls(
            exa_result=exa_result,
            id=completion.id,
            choices=completion.choices,
            created=completion.created,
            model=completion.model,
            object=completion.object,
            system_fingerprint=completion.system_fingerprint,
            usage=completion.usage,
        )
