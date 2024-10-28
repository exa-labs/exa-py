from exa_py import Exa
import os

# Initialize the Exa client
exa = Exa(os.environ.get("EXA_API_KEY"))

response = exa.get_contents(
    ids=["firecrawl.dev"],
    # subpage_target= // specific subpage targets if you have any
    extras={
        "links": 5
    },
)

print(response)

