import os
from metaphor_python import Metaphor

METAPHOR_API_KEY = os.environ.get('METAPHOR_API_KEY')

if not METAPHOR_API_KEY:
    raise ValueError("METAPHOR_API_KEY environment variable not set!")

client = Metaphor(METAPHOR_API_KEY)

response = client.search("funny article about tech culture",
    num_results=5,
    use_autoprompt=True,
    include_domains=["nytimes.com", "wsj.com"],
    start_published_date="2023-06-12",
    filter_options=('score', 'author')
)

print(response.filtered_dict)
