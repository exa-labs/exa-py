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

response = client.search("funny article about tech culture",
    num_results=5,
    includeDomains: ["nytimes.com", "wsj.com"],
    startPublishedDate: "2023-06-12"
)

for result in response.results:
    print(result.title, result.url)
```

## Find Similar

```python
response = client.find_similar("https://waitbutwhy.com/2014/05/fermi-paradox.html", num_results=5)

for result in response.results:
    print(result.title, result.url)
```

## Retrieve Document Contents
```python
ids = ["8U71IlQ5DUTdsZFherhhYA", "X3wd0PbJmAvhu_DQjDKA7A"]
response = client.get_contents(ids)

for content in response.contents:
    print(content.title, content.url)
```

# Contribution
Contributions to metaphor-python are very welcome! Feel free to submit pull requests or raise issues.
