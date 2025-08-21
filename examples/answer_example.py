from exa_py import Exa
from pydantic import BaseModel, Field
import os

exa = Exa(os.environ.get("EXA_API_KEY"))


def print_example(title: str, response):
    print(f"\n{'=' * 20} {title} {'=' * 20}")
    print(response)
    print(f"{'=' * 60}\n")


# Basic answer
response = exa.answer("What is the population of the US?")
print_example("Basic answer", response)

# Answer with full text
response = exa.answer(
    "What is the meaning of life? ",
    text=True,
)
print_example("Answer with full text", response)

# Answer with system prompt
response = exa.answer(
    "What is the latest valuation of SpaceX?",
    system_prompt="Answer only in a single sentence.",
)
print_example("Answer with system prompt", response)

# Answer with streaming
print(f"\n{'=' * 20} Answer with streaming {'=' * 20}")
response = exa.stream_answer(
    "How close are we to meeting aliens?",
    system_prompt="Answer in a humorous tone.",
)
for chunk in response:
    print(chunk, end="", flush=True)
print(f"\n{'=' * 60}\n")

# Answer with output schema dict
response = exa.answer(
    "What is the latest valuation of SpaceX?",
    output_schema={
        "type": "object",
        "required": ["answer"],
        "additionalProperties": False,
        "properties": {
            "answer": {"type": "number"},
        },
    },
)
print_example("Answer with output schema dict", response)


# Answer with output schema pydantic
class SpaceXValuation(BaseModel):
    answer: float = Field(..., description="The latest valuation of SpaceX in USD")


response = exa.answer(
    "What is the latest valuation of SpaceX?",
    output_schema=SpaceXValuation,
)
print_example("Answer with output schema pydantic", response)
