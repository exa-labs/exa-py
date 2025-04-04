import os
from exa_py.api import AsyncExa

EXA_API_KEY = os.environ.get('EXA_API_KEY')

if not EXA_API_KEY:
    raise ValueError("EXA_API_KEY environment variable not set!")

exa = AsyncExa(EXA_API_KEY)

async def main():
    response = await exa.search_and_contents(
        "top cryptocurrency prices today",
        num_results=1,
        livecrawl="always"
    )
    print(response)

    norm_response = await exa.search_and_contents("top cryptocurrency prices today", num_results=1)
    print(norm_response)

    # assert(response.results[0].text != norm_response.results[0].text)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
