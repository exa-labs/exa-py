# Metaphor Python

[![pypi](https://img.shields.io/pypi/v/metaphor-python.svg)](https://pypi.python.org/pypi/metaphor-python)


The Metaphor Python library provides convenient access to the Metaphor API from
applications written in the Python language. It includes a pre-defined set of
classes for API resources that initialize themselves dynamically from API
responses which makes it compatible with a wide range of versions of the Metaphor
API.

## Documentation

See the [Python API docs](https://docs.metaphor.systems/reference/getting-started-1).

See [video demonstration](https://www.youtube.com/watch?v=YfSkX-KzWz0) covering how to use the API.

## Installation

Install `metaphor-python` via pip:

```bash
pip install metaphor-python
```

To install this package from source to make modifications to it, run the following command from the root of the repository:

```bash
python setup.py install
```

## Usage

Import the package and initialize the Metaphor client with your API key which is available in your [Metaphor Dashboard](https://dashboard.metaphor.systems/overview):

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

You can learn more in our [basic search guide](https://docs.metaphor.systems/reference/search-2).

## Find Similar

```python
response = client.find_similar("https://waitbutwhy.com/2014/05/fermi-paradox.html", num_results=5)

for result in response.results:
    print(result.title, result.url)
```

You can learn more in our [basic finding similar links guide](https://docs.metaphor.systems/reference/search-copy).

## Retrieve Document Contents

```python
ids = ["8U71IlQ5DUTdsZFherhhYA", "X3wd0PbJmAvhu_DQjDKA7A"]
response = client.get_contents(ids)

for content in response.contents:
    print(content.title, content.url)
```

You can learn more in our [basic content retrieval guide](https://docs.metaphor.systems/reference/get-contents-of-webpage).

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

This function searches for related links on the Metaphor API.

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

### `Metaphor.get_contents()`

This function retrieves the contents of documents based on a list of document IDs.

#### Args:
- ids (List[str]): A list of document IDs to retrieve the contents for.

#### Returns
`GetContentsResponse`: A dataclass containing the contents of the requested documents.

# Contribution
Contributions to metaphor-python are very welcome! Feel free to submit pull requests or raise issues.

