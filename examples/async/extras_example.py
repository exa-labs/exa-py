from exa_py import AsyncExa
import os

# Initialize the Exa client
exa = AsyncExa(os.environ.get("EXA_API_KEY"))

async def main():
    response = await exa.get_contents(
        urls=["firecrawl.dev"],
        # subpage_target= // specific subpage targets if you have any
        extras={
            "links": 5
        },
    )

    print(response)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

