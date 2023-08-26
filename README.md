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
    include_domains=["nytimes.com", "wsj.com"],
    start_published_date="2023-06-12"
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

## Reference

### `Metaphor.search()`

This function performs a search on the Metaphor API.

#### Args

- query (str): The search query.
- **options**: Additional search options. Valid options are:
  - `num_results` (int): The number of search results to return.
  - `include_domains` (list): A list of domains to include in the search.
  - `exclude_domains` (list): A list of domains to exclude from the search.
  - `start_crawl_date` (str): The start date for the crawl (in YYYY-MM-DD format).
  - `end_crawl_date` (str): The end date for the crawl (in YYYY-MM-DD format).
  - `start_published_date` (str): The start date for when the document was published (in YYYY-MM-DD format).
  - `end_published_date` (str): The end date for when the document was published (in YYYY-MM-DD format).
  - `use_autoprompt` (bool): Whether to use autoprompt for the search.
  - `type` (str): The type of search, 'keyword' or 'neural'. Default: neural

#### Returns
`SearchResponse`: A dataclass containing the search results.

### `Metaphor.find_similar()`

#### Args:
- url (str): The base url to find similar links with.
- **options**: Additional search options. Valid options are:
    - `num_results` (int): The number of search results to return.
    - `include_domains` (list): A list of domains to include in the search.
    - `exclude_domains` (list): A list of domains to exclude from the search.
    - `start_crawl_date` (str): The start date for the crawl (in YYYY-MM-DD format).
    - `end_crawl_date` (str): The end date for the crawl (in YYYY-MM-DD format).
    - `start_published_date` (str): The start date for when the document was published (in YYYY-MM-DD format).
    - `end_published_date` (str): The end date for when the document was published (in YYYY-MM-DD format).

#### Returns
`SearchResponse`: A dataclass containing the search results.

# Contribution
Contributions to metaphor-python are very welcome! Feel free to submit pull requests or raise issues.

