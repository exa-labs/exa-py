import os
from exa_py import Exa

EXA_API_KEY = os.environ.get('EXA_API_KEY')

if not EXA_API_KEY:
    raise ValueError("EXA_API_KEY environment variable not set!")

exa = Exa(EXA_API_KEY)

response = exa.search("funny article about tech culture",
    num_results=5,
    use_autoprompt=True,
    include_domains=["nytimes.com", "wsj.com"],
    start_published_date="2023-06-12"
)

print(response)
