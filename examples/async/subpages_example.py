from dotenv import load_dotenv
from exa_py import AsyncExa
import os

# Load environment variables from .env file
load_dotenv()

# Initialize the Exa client
exa = AsyncExa(os.environ.get("EXA_API_KEY"))

async def main():
    response = await exa.get_contents(
        urls=["firecrawl.dev"],
        # subpage_target= // specific subpage targets if you have any
        subpages=2,
        livecrawl="always",
        highlights=True,
    )

    print(response)

    print("SEARCH SUBPAGES")

    response = await exa.search(
        "canonical url of tesla motors",
        num_results=1,
        contents={"subpages": 2, "highlights": True},
    )

    print(response)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
