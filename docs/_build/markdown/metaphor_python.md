# metaphor_python package

## Submodules

## metaphor_python.api module

### *class* metaphor_python.api.DocumentContent(id: str, url: str, title: str, extract: str, author: str | None = None, \*\*kwargs)

Bases: `object`

A class representing the content of a document.

#### id

The ID of the document.

* **Type:**
  str

#### url

The URL of the document.

* **Type:**
  str

#### title

The title of the document.

* **Type:**
  str

#### extract

The first 1000 tokens of content in the document.

* **Type:**
  str

#### author

If available, the author of the content.

* **Type:**
  str, optional

#### author*: str | None* *= None*

#### extract*: str*

#### id*: str*

#### title*: str*

#### url*: str*

### *class* metaphor_python.api.GetContentsResponse(contents: List[[DocumentContent](#metaphor_python.api.DocumentContent)])

Bases: `object`

A class representing the response for getting contents of documents.

#### contents

A list of document contents.

* **Type:**
  List[[DocumentContent](#metaphor_python.api.DocumentContent)]

#### contents*: List[[DocumentContent](#metaphor_python.api.DocumentContent)]*

### *class* metaphor_python.api.Metaphor(api_key: str, base_url: str = 'https://api.metaphor.systems', user_agent: str = 'metaphor-python 0.1.21')

Bases: `object`

A client for interacting with the Metaphor Search API.

#### base_url

The base URL for the Metaphor API.

* **Type:**
  str

#### headers

The headers to include in API requests.

* **Type:**
  dict

#### find_similar(url: str, num_results: int | None = None, include_domains: List[str] | None = None, exclude_domains: List[str] | None = None, start_crawl_date: str | None = None, end_crawl_date: str | None = None, start_published_date: str | None = None, end_published_date: str | None = None, exclude_source_domain: bool | None = None)

Find similar links to the link provided.

* **Parameters:**
  * **url** (*str*) – The URL for which to find similar links.
  * **num_results** (*int**,* *optional*) – Number of search results to return. Defaults to 10.
  * **include_domains** (*List**[**str**]**,* *optional*) – List of domains to include in the search.
  * **exclude_domains** (*List**[**str**]**,* *optional*) – List of domains to exclude in the search.
  * **start_crawl_date** (*str**,* *optional*) – Results will only include links crawled after this date.
  * **end_crawl_date** (*str**,* *optional*) – Results will only include links crawled before this date.
  * **start_published_date** (*str**,* *optional*) – Results will only include links with a published date after this date.
  * **end_published_date** (*str**,* *optional*) – Results will only include links with a published date before this date.
  * **exclude_source_domain** (*bool**,* *optional*) – If true, exclude links from the base domain of the input URL. Defaults to True.
* **Returns:**
  The response containing search results.
* **Return type:**
  [SearchResponse](#metaphor_python.api.SearchResponse)

#### get_contents(ids: List[str])

Retrieve contents of documents based on a list of document IDs.

* **Parameters:**
  **ids** (*List**[**str**]*) – An array of document IDs obtained from either /search or /findSimilar endpoints.
* **Returns:**
  The response containing document contents.
* **Return type:**
  [GetContentsResponse](#metaphor_python.api.GetContentsResponse)

#### search(query: str, num_results: int | None = None, include_domains: List[str] | None = None, exclude_domains: List[str] | None = None, start_crawl_date: str | None = None, end_crawl_date: str | None = None, start_published_date: str | None = None, end_published_date: str | None = None, use_autoprompt: bool | None = None, type: str | None = None)

Perform a search with a Metaphor prompt-engineered query and retrieve a list of relevant results.

* **Parameters:**
  * **query** (*str*) – The query string.
  * **num_results** (*int**,* *optional*) – Number of search results to return. Defaults to 10.
  * **include_domains** (*List**[**str**]**,* *optional*) – List of domains to include in the search.
  * **exclude_domains** (*List**[**str**]**,* *optional*) – List of domains to exclude in the search.
  * **start_crawl_date** (*str**,* *optional*) – Results will only include links crawled after this date.
  * **end_crawl_date** (*str**,* *optional*) – Results will only include links crawled before this date.
  * **start_published_date** (*str**,* *optional*) – Results will only include links with a published date after this date.
  * **end_published_date** (*str**,* *optional*) – Results will only include links with a published date before this date.
  * **use_autoprompt** (*bool**,* *optional*) – If true, convert query to a Metaphor query. Defaults to False.
  * **type** (*str**,* *optional*) – The type of search, ‘keyword’ or ‘neural’. Defaults to “neural”.
* **Returns:**
  The response containing search results and optional autoprompt string.
* **Return type:**
  [SearchResponse](#metaphor_python.api.SearchResponse)

### *class* metaphor_python.api.Result(title: str, url: str, id: str, score: float | None = None, published_date: str | None = None, author: str | None = None, \*\*kwargs)

Bases: `object`

A class representing a search result.

#### title

The title of the search result.

* **Type:**
  str

#### url

The URL of the search result.

* **Type:**
  str

#### id

The temporary ID for the document.

* **Type:**
  str

#### score

A number from 0 to 1 representing similarity between the query/url and the result.

* **Type:**
  float, optional

#### published_date

An estimate of the creation date, from parsing HTML content.

* **Type:**
  str, optional

#### author

If available, the author of the content.

* **Type:**
  str, optional

#### author*: str | None* *= None*

#### extract*: str | None* *= None*

#### id*: str*

#### published_date*: str | None* *= None*

#### score*: float | None* *= None*

#### title*: str*

#### url*: str*

### *class* metaphor_python.api.SearchResponse(results: List[[Result](#metaphor_python.api.Result)], autoprompt_string: str | None = None)

Bases: `object`

A class representing the response for a search operation.

#### results

A list of search results.

* **Type:**
  List[[Result](#metaphor_python.api.Result)]

#### autoprompt_string

The Metaphor query created by the autoprompt functionality.

* **Type:**
  str, optional

#### api*: [Metaphor](#metaphor_python.api.Metaphor) | None* *= None*

#### autoprompt_string*: str | None* *= None*

#### get_contents()

Retrieve the contents of documents from the search results.

* **Returns:**
  The response containing the retrieved contents.
* **Return type:**
  [GetContentsResponse](#metaphor_python.api.GetContentsResponse)
* **Raises:**
  **Exceptions** – If the API client is not set. (The SearchResponse object was not returned by the search method of a Metaphor client)

#### results*: List[[Result](#metaphor_python.api.Result)]*

### metaphor_python.api.camel_to_snake(camel_str: str)

Convert camelCase string to snake_case.

* **Parameters:**
  **camel_str** (*str*) – The string in camelCase format.
* **Returns:**
  The string converted to snake_case format.
* **Return type:**
  str

### metaphor_python.api.snake_to_camel(snake_str: str)

Convert snake_case string to camelCase.

* **Parameters:**
  **snake_str** (*str*) – The string in snake_case format.
* **Returns:**
  The string converted to camelCase format.
* **Return type:**
  str

### metaphor_python.api.to_camel_case(data: dict)

Convert keys in a dictionary from snake_case to camelCase.

* **Parameters:**
  **data** (*dict*) – The dictionary with keys in snake_case format.
* **Returns:**
  The dictionary with keys converted to camelCase format.
* **Return type:**
  dict

### metaphor_python.api.to_snake_case(data: dict)

Convert keys in a dictionary from camelCase to snake_case.

* **Parameters:**
  **data** (*dict*) – The dictionary with keys in camelCase format.
* **Returns:**
  The dictionary with keys converted to snake_case format.
* **Return type:**
  dict

### metaphor_python.api.validate_find_similar_options(options: Dict[str, object | None])

Validate find similar options against expected types and constraints.

* **Parameters:**
  **options** (*Dict**[**str**,* *Optional**[**object**]**]*) – The find similar options to validate.
* **Raises:**
  **ValueError** – If an invalid option or option type is provided.

### metaphor_python.api.validate_search_options(options: Dict[str, object | None])

Validate search options against expected types and constraints.

* **Parameters:**
  **options** (*Dict**[**str**,* *Optional**[**object**]**]*) – The search options to validate.
* **Raises:**
  **ValueError** – If an invalid option or option type is provided.

## Module contents
