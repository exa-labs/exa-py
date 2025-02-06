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

#Answer with streaming
response = exa.stream_answer(
    "How close are we to meeting aliens?",
)

for chunk in response:
    print(chunk, end='', flush=True)
