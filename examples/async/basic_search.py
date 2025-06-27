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
    
    # Example using include_urls to search within specific URLs
    response_with_urls = await exa.search("artificial intelligence research",
        num_results=3,
        include_urls=["https://arxiv.org/*", "https://openai.com/blog/*"],
    )

    print("\nResults with include_urls:")
    print(response_with_urls)

    # Example using exclude_urls to avoid specific URLs
    response_exclude_urls = await exa.search("machine learning tutorials",
        num_results=5,
        exclude_urls=["https://example-spam-site.com/*"],
        include_domains=["medium.com", "towardsdatascience.com"],
    )

    print("\nResults with exclude_urls:")
    print(response_exclude_urls)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
