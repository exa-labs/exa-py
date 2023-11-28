# metaphor_python package

## Submodules

## metaphor_python.api module

### *class* metaphor_python.api.DocumentContent(id: str, url: str, title: str, extract: str, author: str | None = None, \*\*kwargs)

Bases: `object`

Data class for containing document content information.

#### author*: str | None* *= None*

#### extract*: str*

#### id*: str*

#### title*: str*

#### url*: str*

### *class* metaphor_python.api.GetContentsResponse(contents: List[[DocumentContent](#metaphor_python.api.DocumentContent)])

Bases: `object`

Data class for containing the response when getting contents.

#### contents*: List[[DocumentContent](#metaphor_python.api.DocumentContent)]*

### *class* metaphor_python.api.Metaphor(api_key: str, base_url: str = 'https://api.metaphor.systems', user_agent: str = 'metaphor-python 0.1.21')

Bases: `object`

A class for interacting with the Metaphor API.

#### find_similar(url: str, num_results: int | None = None, include_domains: List[str] | None = None, exclude_domains: List[str] | None = None, start_crawl_date: str | None = None, end_crawl_date: str | None = None, start_published_date: str | None = None, end_published_date: str | None = None, exclude_source_domain: bool | None = None)

Find similar links to the link provided.

* **Parameters:**
  * **url** (*str*) – The URL for which to find similar links.
  * **num_results** (*Optional**[**int**]*) – Number of search results to return (Default is 10, max 10 for basic plans).
  * **include_domains** (*Optional**[**List**[**str**]**]*) – An optional list of domain names to include in the search.
  * **exclude_domains** (*Optional**[**List**[**str**]**]*) – An optional list of domain names to exclude from the search.
  * **start_crawl_date** (*Optional**[**str**]*) – The optional start date (inclusive) for the crawled data in ISO 8601 format.
  * **end_crawl_date** (*Optional**[**str**]*) – The optional end date (inclusive) for the crawled data in ISO 8601 format.
  * **start_published_date** (*Optional**[**str**]*) – The optional start date (inclusive) for the published data in ISO 8601 format.
  * **end_published_date** (*Optional**[**str**]*) – The optional end date (inclusive) for the published data in ISO 8601 format.
  * **exclude_source_domain** (*Optional**[**bool**]*) – If true, links from the base domain of the input will be excluded (Default is true).
* **Returns:**
  A dictionary object with a list of similar search results.

#### get_contents(ids: List[str])

Retrieve contents of documents based on a list of document IDs.

* **Parameters:**
  **ids** (*List**[**str**]*) – An array of document IDs obtained from either /search or /findSimilar endpoints.
* **Returns:**
  A dictionary object containing the contents of the documents.

#### search(query: str, num_results: int | None = None, include_domains: List[str] | None = None, exclude_domains: List[str] | None = None, start_crawl_date: str | None = None, end_crawl_date: str | None = None, start_published_date: str | None = None, end_published_date: str | None = None, use_autoprompt: bool | None = None, type: str | None = None)

Perform a search with a Metaphor prompt-engineered query and retrieve a list of relevant results.

* **Parameters:**
  * **query** (*str*) – The query string in the form of a declarative suggestion.
  * **num_results** (*Optional**[**int**]*) – Number of search results to return (Default is 10, max 10 for basic plans).
  * **include_domains** (*Optional**[**List**[**str**]**]*) – List of domains to include in the search.
  * **exclude_domains** (*Optional**[**List**[**str**]**]*) – List of domains to exclude in the search.
  * **start_crawl_date** (*Optional**[**str**]*) – Results will only include links crawled after this date in ISO 8601 format.
  * **end_crawl_date** (*Optional**[**str**]*) – Results will only include links crawled before this date in ISO 8601 format.
  * **start_published_date** (*Optional**[**str**]*) – Only links with a published date after this date will be returned in ISO 8601 format.
  * **end_published_date** (*Optional**[**str**]*) – Only links with a published date before this date will be returned in ISO 8601 format.
  * **use_autoprompt** (*Optional**[**bool**]*) – If true, query will be converted to a Metaphor query (Default is false).
  * **type** (*Optional**[**str**]*) – The type of search, either ‘keyword’ or ‘neural’ (Default is neural).
* **Returns:**
  A dictionary object with a list of search results and possibly an autopromptString.

### *class* metaphor_python.api.Result(title: str, url: str, id: str, score: float | None = None, published_date: str | None = None, author: str | None = None, \*\*kwargs)

Bases: `object`

Data class for containing the result information.

#### author*: str | None* *= None*

#### extract*: str | None* *= None*

#### id*: str*

#### published_date*: str | None* *= None*

#### score*: float | None* *= None*

#### title*: str*

#### url*: str*

### *class* metaphor_python.api.SearchResponse(results: List[[Result](#metaphor_python.api.Result)], autoprompt_string: str | None = None)

Bases: `object`

Data class for containing the search response.

#### api*: [Metaphor](#metaphor_python.api.Metaphor) | None* *= None*

#### autoprompt_string*: str | None* *= None*

#### get_contents()

Retrieve the contents of documents from the search results.

* **Raises:**
  **Exception** – if the API client is not set
* **Returns:**
  A GetContentsResponse object with the retrieved contents
* **Return type:**
  [GetContentsResponse](#metaphor_python.api.GetContentsResponse)

#### results*: List[[Result](#metaphor_python.api.Result)]*

### metaphor_python.api.camel_to_snake(camel_str: str)

Convert a camelCase string to a snake_case string.

* **Parameters:**
  **camel_str** (*str*) – A string in camelCase format to be converted
* **Returns:**
  The converted snake_case string
* **Return type:**
  str

### metaphor_python.api.snake_to_camel(snake_str: str)

Convert a snake_case string to a camelCase string.

* **Parameters:**
  **snake_str** (*str*) – A string in snake_case format to be converted
* **Returns:**
  The converted camelCase string
* **Return type:**
  str

### metaphor_python.api.to_camel_case(data: dict)

Convert all keys of the given dictionary from snake_case to camelCase.

* **Parameters:**
  **data** (*dict*) – A dictionary with keys in snake_case format
* **Returns:**
  New dictionary with keys converted to camelCase format
* **Return type:**
  dict

### metaphor_python.api.to_snake_case(data: dict)

Convert all keys of the given dictionary from camelCase to snake_case.

* **Parameters:**
  **data** (*dict*) – A dictionary with keys in camelCase format
* **Returns:**
  New dictionary with keys converted to snake_case format
* **Return type:**
  dict

### metaphor_python.api.validate_find_similar_options(options: Dict[str, object | None])

Validate the find similar options against the expected types defined in FIND_SIMILAR_OPTIONS_TYPES.

* **Parameters:**
  **options** (*Dict**[**str**,* *Optional**[**object**]**]*) – A dictionary containing the find similar options and their values
* **Raises:**
  **ValueError** – if an invalid option or option type is detected

### metaphor_python.api.validate_search_options(options: Dict[str, object | None])

Validate the search options against the expected types defined in SEARCH_OPTIONS_TYPES.

* **Parameters:**
  **options** (*Dict**[**str**,* *Optional**[**object**]**]*) – A dictionary containing the search options and their values
* **Raises:**
  **ValueError** – if an invalid option or option type is detected

## Module contents
