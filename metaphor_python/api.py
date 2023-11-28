import re
import requests
from typing import List, Optional, Dict
from dataclasses import dataclass, field

def snake_to_camel(snake_str: str) -> str:
    """Convert a snake_case string to a camelCase string.
    
    :param snake_str: A string in snake_case format to be converted
    :type snake_str: str
    :return: The converted camelCase string
    :rtype: str
    """
    components = snake_str.split("_")
    return components[0] + "".join(x.title() for x in components[1:])

def to_camel_case(data: dict) -> dict:
    """Convert all keys of the given dictionary from snake_case to camelCase.
    
    :param data: A dictionary with keys in snake_case format
    :type data: dict
    :return: New dictionary with keys converted to camelCase format
    :rtype: dict
    """
    return {snake_to_camel(k): v for k, v in data.items() if v is not None}

def camel_to_snake(camel_str: str) -> str:
    """Convert a camelCase string to a snake_case string.
    
    :param camel_str: A string in camelCase format to be converted
    :type camel_str: str
    :return: The converted snake_case string
    :rtype: str
    """
    snake_str = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", camel_str)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", snake_str).lower()

def to_snake_case(data: dict) -> dict:
    """Convert all keys of the given dictionary from camelCase to snake_case.
    
    :param data: A dictionary with keys in camelCase format
    :type data: dict
    :return: New dictionary with keys converted to snake_case format
    :rtype: dict
    """
    return {camel_to_snake(k): v for k, v in data.items()}

SEARCH_OPTIONS_TYPES = {
    'query': str,  # Declarative suggestion for search.
    'num_results': int,  # Number of results (Default: 10, Max for basic: 10).
    'include_domains': list,  # Domains to search from; exclusive with 'exclude_domains'.
    'exclude_domains': list,  # Domains to omit; exclusive with 'include_domains'.
    'start_crawl_date': str,  # Results after this crawl date. ISO 8601 format.
    'end_crawl_date': str,  # Results before this crawl date. ISO 8601 format.
    'start_published_date': str,  # Results after this publish date; excludes links with no date. ISO 8601 format.
    'end_published_date': str,  # Results before this publish date; excludes links with no date. ISO 8601 format.
    'use_autoprompt': bool,  # Convert query to Metaphor (Higher latency, Default: false).
    'type': str,  # 'keyword' or 'neural' (Default: neural). Choose 'neural' for high-quality, semantically relevant content in popular domains. 'Keyword' is for specific, local, or obscure queries.
}

FIND_SIMILAR_OPTIONS_TYPES = {
    'url': str, # The url for which you would like to find similar links
    'num_results': int,
    'include_domains': list,
    'exclude_domains': list,
    'start_crawl_date': str,
    'end_crawl_date': str,
    'start_published_date': str,
    'end_published_date': str,
    'exclude_source_domain': bool,
}

def validate_search_options(options: Dict[str, Optional[object]]) -> None:
    """Validate the search options against the expected types defined in SEARCH_OPTIONS_TYPES.
    
    :param options: A dictionary containing the search options and their values
    :type options: Dict[str, Optional[object]]
    :raises ValueError: if an invalid option or option type is detected
    """
    for key, value in options.items():
        if key not in SEARCH_OPTIONS_TYPES:
            raise ValueError(f"Invalid option: '{key}'")
        if not isinstance(value, SEARCH_OPTIONS_TYPES[key]):
            raise ValueError(f"Invalid type for option '{key}': Expected {SEARCH_OPTIONS_TYPES[key]}, got {type(value)}")
        if key in ['include_domains', 'exclude_domains'] and not value:
            raise ValueError(f"Invalid value for option '{key}': cannot be an empty list")

def validate_find_similar_options(options: Dict[str, Optional[object]]) -> None:
    """Validate the find similar options against the expected types defined in FIND_SIMILAR_OPTIONS_TYPES.
    
    :param options: A dictionary containing the find similar options and their values
    :type options: Dict[str, Optional[object]]
    :raises ValueError: if an invalid option or option type is detected
    """
    for key, value in options.items():
        if key not in FIND_SIMILAR_OPTIONS_TYPES:
            raise ValueError(f"Invalid option: '{key}'")
        if not isinstance(value, FIND_SIMILAR_OPTIONS_TYPES[key]):
            raise ValueError(f"Invalid type for option '{key}': Expected {FIND_SIMILAR_OPTIONS_TYPES[key]}, got {type(value)}")
        if key in ['include_domains', 'exclude_domains'] and not value:
            raise ValueError(f"Invalid value for option '{key}': cannot be an empty list")

@dataclass
class Result:
    """Data class for containing the result information."""
    title: str
    url: str
    id: str
    score: Optional[float] = None
    published_date: Optional[str] = None
    author: Optional[str] = None
    extract: Optional[str] = None

    def __init__(self, title: str, url: str, id: str, score: Optional[float] = None, published_date: Optional[str] = None, author: Optional[str] = None, **kwargs):
        self.title = title
        self.url = url
        self.score = score
        self.id = id
        self.published_date = published_date
        self.author = author
    def __str__(self):
        return (f"Title: {self.title}\n"
                f"URL: {self.url}\n"
                f"ID: {self.id}\n"
                f"Score: {self.score}\n"
                f"Published Date: {self.published_date}\n"
                f"Author: {self.author}\n"
                f"Extract: {self.extract}")

@dataclass
class DocumentContent:
    """Data class for containing document content information."""
    id: str
    url: str
    title: str
    extract: str
    author: Optional[str] = None

    def __init__(self, id: str, url: str, title: str, extract: str, author: Optional[str] = None, **kwargs):
        self.id = id
        self.url = url
        self.title = title
        self.extract = extract
        self.author = author

    def __str__(self):
        return (f"ID: {self.id}\n"
                f"URL: {self.url}\n"
                f"Title: {self.title}\n"
                f"Extract: {self.extract}"
                f"Author: {self.author}")

@dataclass
class GetContentsResponse:
    """Data class for containing the response when getting contents."""
    contents: List[DocumentContent]

    def __str__(self):
        return "\n\n".join(str(content) for content in self.contents)

@dataclass
class SearchResponse:
    """Data class for containing the search response."""
    results: List[Result]
    autoprompt_string: Optional[str] = None
    api: Optional['Metaphor'] = field(default=None, init=False)

    def get_contents(self):
        """Retrieve the contents of documents from the search results.
        
        :raises Exception: if the API client is not set
        :return: A GetContentsResponse object with the retrieved contents
        :rtype: GetContentsResponse
        """
        if self.api is None:
            raise Exception("API client is not set. This method should be called on a SearchResponse returned by the 'search' method of 'Metaphor'.")
        ids = [result.id for result in self.results]
        return self.api.get_contents(ids)

    def __str__(self):
        output = "\n\n".join(str(result) for result in self.results)
        if self.autoprompt_string:
            output += f"\n\nAutoprompt String: {self.autoprompt_string}"
        return output

class Metaphor:
    """A class for interacting with the Metaphor API."""
    def __init__(self, api_key: str, base_url: str = "https://api.metaphor.systems", user_agent: str = "metaphor-python 0.1.21"):
        """
        Initialize a Metaphor API client.

        :param api_key: Your API key for accessing the Metaphor API
        :type api_key: str
        :param base_url: Base URL for the Metaphor API (default: "https://api.metaphor.systems")
        :type base_url: str, optional
        :param user_agent: The User-Agent string to send with requests (default: "metaphor-python 0.1.21")
        :type user_agent: str, optional
        """
        self.base_url = base_url
        self.headers = {"x-api-key": api_key, "User-Agent": user_agent}

    def search(self, query: str, num_results: Optional[int] = None, include_domains: Optional[List[str]] = None,
               exclude_domains: Optional[List[str]] = None, start_crawl_date: Optional[str] = None,
               end_crawl_date: Optional[str] = None, start_published_date: Optional[str] = None,
               end_published_date: Optional[str] = None, use_autoprompt: Optional[bool] = None,
               type: Optional[str] = None) -> SearchResponse:
        """
        Perform a search with a Metaphor prompt-engineered query and retrieve a list of relevant results.

        :param query: The query string in the form of a declarative suggestion.
        :type query: str
        :param num_results: Number of search results to return (Default is 10, max 10 for basic plans).
        :type num_results: Optional[int]
        :param include_domains: List of domains to include in the search.
        :type include_domains: Optional[List[str]]
        :param exclude_domains: List of domains to exclude in the search.
        :type exclude_domains: Optional[List[str]]
        :param start_crawl_date: Results will only include links crawled after this date in ISO 8601 format.
        :type start_crawl_date: Optional[str]
        :param end_crawl_date: Results will only include links crawled before this date in ISO 8601 format.
        :type end_crawl_date: Optional[str]
        :param start_published_date: Only links with a published date after this date will be returned in ISO 8601 format.
        :type start_published_date: Optional[str]
        :param end_published_date: Only links with a published date before this date will be returned in ISO 8601 format.
        :type end_published_date: Optional[str]
        :param use_autoprompt: If true, query will be converted to a Metaphor query (Default is false).
        :type use_autoprompt: Optional[bool]
        :param type: The type of search, either 'keyword' or 'neural' (Default is neural).
        :type type: Optional[str]
        :return: A dictionary object with a list of search results and possibly an autopromptString.
        """
        options = {k: v for k, v in locals().items() if k != 'self' and v is not None}
        validate_search_options(options)
        request = {'query': query}
        request.update(to_camel_case(options))
        response = requests.post(f"{self.base_url}/search", json=request, headers=self.headers)
        if response.status_code != 200:
            raise Exception(f"Request failed with status code {response.status_code}. Message: {response.text}")
        results = [Result(**to_snake_case(result)) for result in response.json()["results"]]
        autoprompt_string = response.json()["autopromptString"] if "autopromptString" in response.json() else None
        search_response = SearchResponse(results=results, autoprompt_string=autoprompt_string)
        search_response.api = self
        return search_response

    def find_similar(self, url: str, num_results: Optional[int] = None, include_domains: Optional[List[str]] = None,
                     exclude_domains: Optional[List[str]] = None, start_crawl_date: Optional[str] = None,
                     end_crawl_date: Optional[str] = None, start_published_date: Optional[str] = None,
                     end_published_date: Optional[str] = None, exclude_source_domain:Optional[bool] = None) -> SearchResponse:
        """
        Find similar links to the link provided.

        :param url: The URL for which to find similar links.
        :type url: str
        :param num_results: Number of search results to return (Default is 10, max 10 for basic plans).
        :type num_results: Optional[int]
        :param include_domains: An optional list of domain names to include in the search.
        :type include_domains: Optional[List[str]]
        :param exclude_domains: An optional list of domain names to exclude from the search.
        :type exclude_domains: Optional[List[str]]
        :param start_crawl_date: The optional start date (inclusive) for the crawled data in ISO 8601 format.
        :type start_crawl_date: Optional[str]
        :param end_crawl_date: The optional end date (inclusive) for the crawled data in ISO 8601 format.
        :type end_crawl_date: Optional[str]
        :param start_published_date: The optional start date (inclusive) for the published data in ISO 8601 format.
        :type start_published_date: Optional[str]
        :param end_published_date: The optional end date (inclusive) for the published data in ISO 8601 format.
        :type end_published_date: Optional[str]
        :param exclude_source_domain: If true, links from the base domain of the input will be excluded (Default is true).
        :type exclude_source_domain: Optional[bool]
        :return: A dictionary object with a list of similar search results.
        """
        options = {k: v for k, v in locals().items() if k != 'self' and v is not None}
        validate_find_similar_options(options)
        request = {'url': url}
        request.update(to_camel_case(options))
        response = requests.post(f"{self.base_url}/findSimilar", json=request, headers=self.headers)
        if response.status_code != 200:
            raise Exception(f"Request failed with status code {response.status_code}. Message: {response.text}")
        results = [Result(**to_snake_case(result)) for result in response.json()["results"]]
        find_similar_response = SearchResponse(results=results)
        find_similar_response.api = self
        return find_similar_response

    def get_contents(self, ids: List[str]) -> GetContentsResponse:
        """
        Retrieve contents of documents based on a list of document IDs.

        :param ids: An array of document IDs obtained from either /search or /findSimilar endpoints.
        :type ids: List[str]
        :return: A dictionary object containing the contents of the documents.
        """
        if len(ids) == 0:
            return GetContentsResponse([])
        response = requests.get(f"{self.base_url}/contents", params=to_camel_case({"ids": ids}), headers=self.headers)
        if response.status_code != 200:
            raise Exception(f"Request failed with status code {response.status_code}. Message: {response.text}")
        return GetContentsResponse([DocumentContent(**to_snake_case(document)) for document in response.json()["contents"]])
