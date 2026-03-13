import os
from exa_py import Exa

EXA_API_KEY = os.environ.get('EXA_API_KEY')

if not EXA_API_KEY:
    raise ValueError("EXA_API_KEY environment variable not set!")

exa = Exa(EXA_API_KEY)

response = exa.search("upcoming marvel movies release dates",
    num_results=1,
    contents={"text": True, "livecrawl": "always"}
)
print(response)

norm_response = exa.search(
    "upcoming marvel movies release dates",
    num_results=1,
    contents={"text": True},
)
print(norm_response)

# assert(response.results[0].text != norm_response.results[0].text)
