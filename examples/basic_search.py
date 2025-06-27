import os
from exa_py import Exa

EXA_API_KEY = os.environ.get('EXA_API_KEY')

if not EXA_API_KEY:
    raise ValueError("EXA_API_KEY environment variable not set!")

exa = Exa(EXA_API_KEY)

response = exa.search("funny article about tech culture",
    num_results=5,
    include_domains=["nytimes.com", "wsj.com"],
    start_published_date="2023-06-12",
)

print(response)

# Example using include_urls to search within specific URLs
response_with_urls = exa.search("artificial intelligence research",
    num_results=3,
    include_urls=["https://arxiv.org/*", "https://openai.com/blog/*"],
)

print("\nResults with include_urls:")
print(response_with_urls)

# Example using exclude_urls to avoid specific URLs
response_exclude_urls = exa.search("machine learning tutorials",
    num_results=5,
    exclude_urls=["https://example-spam-site.com/*"],
    include_domains=["medium.com", "towardsdatascience.com"],
)

print("\nResults with exclude_urls:")
print(response_exclude_urls)
