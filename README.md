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
You can perform a search by creating a SearchRequest object and passing it to the search method:

```python
from metaphor_python import SearchRequest

request = SearchRequest(query="Here is a reaully interesting AI company:", num_results=5)
response = client.search(request)

for result in response.results:
    print(result.title, result.url)
```

## Find Similar
To find documents similar to a given URL, you can use the FindSimilarRequest object:

```python
from metaphor_python import FindSimilarRequest

request = FindSimilarRequest(url="https://example.com/article", num_results=5)
response = client.find_similar(request)

for result in response.results:
    print(result.title, result.url)
```

## Retrieve Document Contents
To retrieve the contents of documents, use the GetContentsRequest object:

from metaphor_python import GetContentsRequest

```python
request = GetContentsRequest(ids=["doc1", "doc2"])
response = client.get_contents(request)

for content in response.contents:
    print(content.title, content.url)
```

# Contribution
Contributions to metaphor-python are very welcome! Feel free to submit pull requests or raise issues.
