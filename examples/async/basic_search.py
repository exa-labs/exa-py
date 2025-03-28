import os
from exa_py import AsyncExa

EXA_API_KEY = os.environ.get('EXA_API_KEY')

if not EXA_API_KEY:
    raise ValueError("EXA_API_KEY environment variable not set!")

exa = AsyncExa(EXA_API_KEY)

async def main():
    response = await exa.search("funny article about tech culture",
        num_results=5,
        include_domains=["nytimes.com", "wsj.com"],
        start_published_date="2023-06-12",
    )

    print(response)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
