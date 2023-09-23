from metaphor_python import Metaphor

client = Metaphor("fa0fcc27-312c-4d5e-b06d-f101f9717e91")

response = client.find_similar("https://waitbutwhy.com/2014/05/fermi-paradox.html", num_results=5)

for result in response.results:
    print(result.title, result.url)