from dotenv import load_dotenv
from exa_py import Exa
import os

# Load environment variables from .env file
load_dotenv()

# Initialize the Exa client
exa = Exa(os.environ.get("EXA_API_KEY"))

response = exa.get_contents(
    ids=["firecrawl.dev"],
    # subpage_target= // specific subpage targets if you have any
    subpages=2,
    livecrawl="always"
)

print(response)


print("SEARCH AND CONTENTS SUBPAGES")

response = exa.search_and_contents(
    "canonical url of tesla motors",
    subpages=2,
    num_results=1,
)

print(response)

print("FIND SIMILAR AND CONTENTS SUBPAGES")

response = exa.find_similar_and_contents(
    "tesla.com",
    subpages=2,
    text=True,
    num_results=1,
)

print(response)
