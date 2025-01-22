from exa_py import Exa
import os

exa = Exa(os.environ.get("EXA_API_KEY"))

# Basic answer
response = exa.answer("This is a query to answer:")
print(response)

# Answer with expanded queries
response = exa.answer(
    "This is a query to answer with expanded queries:",
    expanded_queries_limit=2
)
print(response)

# Answer with full text
response = exa.answer(
    "This is a query to answer with full text:",
    include_text=True
)
print(response) 

#Answer with streaming
response = exa.answer(
    "This is a query to answer with streaming:",
    stream=True
)

# Print each chunk as it arrives
for chunk in response:
    print(chunk)
