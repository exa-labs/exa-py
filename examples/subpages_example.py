from dotenv import load_dotenv
from exa_py import Exa
import os

# Load environment variables from .env file
load_dotenv()

# Initialize the Exa client
exa = Exa(os.environ.get("EXA_API_KEY"))

response = exa.get_contents(
    urls=["firecrawl.dev"],
    # subpage_target= // specific subpage targets if you have any
    subpages=2,
    livecrawl="always",
    highlights=True,
)

print(response)
