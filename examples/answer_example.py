from exa_py import Exa
import os

exa = Exa(os.environ.get("EXA_API_KEY"))

# Basic answer
response = exa.answer("What is the population of the US?")
print(response)

# Answer with full text
response = exa.answer(
    "What is the meaning of life? ",
    text=True,
    model="exa-pro",
)
print(response)

# Answer with system prompt
response = exa.answer(
    "What is the latest valuation of SpaceX?",
    system_prompt="Answer only in a single sentence.",
)
print(response)

#Answer with streaming
response = exa.stream_answer(
    "How close are we to meeting aliens?",
    system_prompt="Answer in a humorous tone.",
)

for chunk in response:
    print(chunk, end='', flush=True)
