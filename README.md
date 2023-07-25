# Metaphor Python

An ergonomic way to use Metaphor in python.

## Installation

Install `metaphor-python` via pip:

```bash
pip install metaphor-python
```

## Usage
Import the package and initialize the Metaphor client with your API key:

```python
from metaphor_python import Metaphor

client = Metaphor(api_key="your-api-key")
```

## Search Request
```python

response = client.search("here is a really interesting AI company", num_results=5)

for result in response.results:
    print(result.title, result.url)
```

## Find Similar

```python
response = client.find_similar("https://example.com/article, num_results=5)

for result in response.results:
    print(result.title, result.url)
```

## Retrieve Document Contents
```python
ids = ["doc1", "doc2"]
response = client.get_contents(request)

for content in response.contents:
    print(content.title, content.url)
```

# Contribution
Contributions to metaphor-python are very welcome! Feel free to submit pull requests or raise issues.
