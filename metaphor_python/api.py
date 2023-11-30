import re
import requests
from typing import List, Optional, Dict
from dataclasses import dataclass, field

def snake_to_camel(snake_str: str) -> str:
    """Convert snake_case string to camelCase.

    Args:
        snake_str (str): The string in snake_case format.

    Returns:
        str: The string converted to camelCase format.
    """
    components = snake_str.split("_")
    return components[0] + "".join(x.title() for x in components[1:])

def to_camel_case(data: dict) -> dict:
    """Convert keys in a dictionary from snake_case to camelCase.

    Args:
        data (dict): The dictionary with keys in snake_case format.

    Returns:
        dict: The dictionary with keys converted to camelCase format.
    """
    return {snake_to_camel(k): v for k, v in data.items() if v is not None}

def camel_to_snake(camel_str: str) -> str:
    """Convert camelCase string to snake_case.

    Args:
        camel_str (str): The string in camelCase format.

    Returns:
        str: The string converted to snake_case format.
    """
    snake_str = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", camel_str)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", snake_str).lower()

def to_snake_case(data: dict) -> dict:
    """Convert keys in a dictionary from camelCase to snake_case.

    Args:
        data (dict): The dictionary with keys in camelCase format.

    Returns:
        dict: The dictionary with keys converted to snake_case format.
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
    'category': str # A data category to focus on, with higher comprehensivity and data cleanliness. Currently, the only category is company.
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
    'category': str
}

def validate_search_options(options: Dict[str, Optional[object]]) -> None:
    """Validate search options against expected types and constraints.

    Args:
        options (Dict[str, Optional[object]]): The search options to validate.

    Raises:
        ValueError: If an invalid option or option type is provided.
    """
    for key, value in options.items():
        if key not in SEARCH_OPTIONS_TYPES:
            raise ValueError(f"Invalid option: '{key}'")
        if not isinstance(value, SEARCH_OPTIONS_TYPES[key]):
            raise ValueError(f"Invalid type for option '{key}': Expected {SEARCH_OPTIONS_TYPES[key]}, got {type(value)}")
        if key in ['include_domains', 'exclude_domains'] and not value:
            raise ValueError(f"Invalid value for option '{key}': cannot be an empty list")

def validate_find_similar_options(options: Dict[str, Optional[object]]) -> None:
    """Validate find similar options against expected types and constraints.

    Args:
        options (Dict[str, Optional[object]]): The find similar options to validate.

    Raises:
        ValueError: If an invalid option or option type is provided.
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
    """A class representing a search result.

    Attributes:
        title (str): The title of the search result.
        url (str): The URL of the search result.
        id (str): The temporary ID for the document.
        score (float, optional): A number from 0 to 1 representing similarity between the query/url and the result.
        published_date (str, optional): An estimate of the creation date, from parsing HTML content.
        author (str, optional): If available, the author of the content.
    """
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
    """A class representing the content of a document.

    Attributes:
        id (str): The ID of the document.
        url (str): The URL of the document.
        title (str): The title of the document.
        extract (str): The first 1000 tokens of content in the document.
        author (str, optional): If available, the author of the content.
    """
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
    """A class representing the response for getting contents of documents.

    Attributes:
        contents (List[DocumentContent]): A list of document contents.
    """
    contents: List[DocumentContent]

    def __str__(self):
        return "\n\n".join(str(content) for content in self.contents)

@dataclass
class SearchResponse:
    """A class representing the response for a search operation.

    Attributes:
        results (List[Result]): A list of search results.
        autoprompt_string (str, optional): The Metaphor query created by the autoprompt functionality.
    """
    results: List[Result]
    autoprompt_string: Optional[str] = None
    api: Optional['Metaphor'] = field(default=None, init=False)

    def get_contents(self):
        """Retrieve the contents of documents from the search results.
        
        Returns:
            GetContentsResponse: The response containing the retrieved contents.
        
        Raises:
            Exceptions: If the API client is not set. (The SearchResponse object was not returned by the `search` method of a `Metaphor` client)
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
    """A client for interacting with the Metaphor Search API.

    Attributes:
        base_url (str): The base URL for the Metaphor API.
        headers (dict): The headers to include in API requests.
    """

    def __init__(self, api_key: str, base_url: str = "https://api.metaphor.systems", user_agent: str = "metaphor-python 0.1.23"):
        """Initialize the Metaphor client with the provided API key and optional base URL and user agent.

        Args:
            api_key (str): The API key for authenticating with the Metaphor API.
            base_url (str, optional): The base URL for the Metaphor API. Defaults to "https://api.metaphor.systems".
            user_agent (str, optional): The user agent string to use for requests. Defaults to "metaphor-python 0.1.21".
        """
        self.base_url = base_url
        self.headers = {"x-api-key": api_key, "User-Agent": user_agent}

    def search(self, query: str, num_results: Optional[int] = None, include_domains: Optional[List[str]] = None,
               exclude_domains: Optional[List[str]] = None, start_crawl_date: Optional[str] = None,
               end_crawl_date: Optional[str] = None, start_published_date: Optional[str] = None,
               end_published_date: Optional[str] = None, use_autoprompt: Optional[bool] = None,
               type: Optional[str] = None, category: Optional[str] = None) -> SearchResponse:
        """Perform a search with a Metaphor prompt-engineered query and retrieve a list of relevant results.

        Args:
            query (str): The query string.
            num_results (int, optional): Number of search results to return. Defaults to 10.
            include_domains (List[str], optional): List of domains to include in the search.
            exclude_domains (List[str], optional): List of domains to exclude in the search.
            start_crawl_date (str, optional): Results will only include links crawled after this date.
            end_crawl_date (str, optional): Results will only include links crawled before this date.
            start_published_date (str, optional): Results will only include links with a published date after this date.
            end_published_date (str, optional): Results will only include links with a published date before this date.
            use_autoprompt (bool, optional): If true, convert query to a Metaphor query. Defaults to False.
            type (str, optional): The type of search, 'keyword' or 'neural'. Defaults to "neural".
            category (str, optional): A data category to focus on, with higher comprehensivity and data cleanliness. Currently, the only category is company.
        Returns:
            SearchResponse: The response containing search results and optional autoprompt string.
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
                     end_published_date: Optional[str] = None, exclude_source_domain:Optional[bool] = None, category: Optional[str] = None) -> SearchResponse:
        """Find similar links to the link provided.

        Args:
            url (str): The URL for which to find similar links.
            num_results (int, optional): Number of search results to return. Defaults to 10.
            include_domains (List[str], optional): List of domains to include in the search.
            exclude_domains (List[str], optional): List of domains to exclude in the search.
            start_crawl_date (str, optional): Results will only include links crawled after this date.
            end_crawl_date (str, optional): Results will only include links crawled before this date.
            start_published_date (str, optional): Results will only include links with a published date after this date.
            end_published_date (str, optional): Results will only include links with a published date before this date.
            exclude_source_domain (bool, optional): If true, exclude links from the base domain of the input URL. Defaults to True.
            category (str, optional): A data category to focus on, with higher comprehensivity and data cleanliness. Currently, the only category is company.
        Returns:
            SearchResponse: The response containing search results.
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
        """Retrieve contents of documents based on a list of document IDs.

        Args:
            ids (List[str]): An array of document IDs obtained from either /search or /findSimilar endpoints.

        Returns:
            GetContentsResponse: The response containing document contents.
        """
        if len(ids) == 0:
            return GetContentsResponse([])
        response = requests.get(f"{self.base_url}/contents", params=to_camel_case({"ids": ids}), headers=self.headers)
        if response.status_code != 200:
            raise Exception(f"Request failed with status code {response.status_code}. Message: {response.text}")
        return GetContentsResponse([DocumentContent(**to_snake_case(document)) for document in response.json()["contents"]])
