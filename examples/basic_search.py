from metaphor_python import Metaphor

client = Metaphor("fa0fcc27-312c-4d5e-b06d-f101f9717e91")

response = client.search("funny article about tech culture",
    num_results=5,
    use_autoprompt=True,
    include_domains=["nytimes.com", "wsj.com"],
    start_published_date="2023-06-12"
)

print(response)
