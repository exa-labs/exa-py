import re
import requests
from typing import List, Optional, Dict
from dataclasses import dataclass, field

def snake_to_camel(snake_str: str) -> str:
    components = snake_str.split("_")
    return components[0] + "".join(x.title() for x in components[1:])

def to_camel_case(data: dict) -> dict:
    return {snake_to_camel(k): v for k, v in data.items() if v is not None}

def camel_to_snake(camel_str: str) -> str:
    snake_str = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", camel_str)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", snake_str).lower()

def to_snake_case(data: dict) -> dict:
    return {camel_to_snake(k): v for k, v in data.items()}

VALID_SEARCH_OPTIONS = {
    'num_results': int,
    'include_domains': list,
    'exclude_domains': list,
    'start_crawl_date': str,
    'end_crawl_date': str,
    'start_published_date': str,
    'end_published_date': str,
    'use_autoprompt': bool,
    'type': str
}

VALID_FIND_SIMILAR_OPTIONS = {
    'num_results': int,
    'include_domains': list,
    'exclude_domains': list,
    'start_crawl_date': str,
    'end_crawl_date': str,
    'start_published_date': str,
    'end_published_date': str,
}

def validate_search_options(options: Dict[str, Optional[object]]) -> None:
    for key, value in options.items():
        if key not in VALID_SEARCH_OPTIONS:
            raise ValueError(f"Invalid option: '{key}'")
        if not isinstance(value, VALID_SEARCH_OPTIONS[key]):
            raise ValueError(f"Invalid type for option '{key}': Expected {VALID_SEARCH_OPTIONS[key]}, got {type(value)}")

def validate_find_similar_options(options: Dict[str, Optional[object]]) -> None:
    for key, value in options.items():
        if key not in VALID_FIND_SIMILAR_OPTIONS:
            raise ValueError(f"Invalid option: '{key}'")
        if not isinstance(value, VALID_FIND_SIMILAR_OPTIONS[key]):
            raise ValueError(f"Invalid type for option '{key}': Expected {VALID_FIND_SIMILAR_OPTIONS[key]}, got {type(value)}")

@dataclass
class Result:
    title: str
    url: str
    id: str
    score: Optional[float] = None
    published_date: Optional[str] = None
    author: Optional[str] = None
    extract: Optional[str] = None # beta field. returned when findSimilar_and_get_contents is called

    def __init__(self, title, url, score, id, published_date=None, author=None, **kwargs):
        self.title = title
        self.url = url
        self.score = score
        self.id = id
        self.published_date = published_date
        self.author = author

@dataclass
class DocumentContent:
    id: str
    url: str
    title: str
    extract: str

    def __init__(self, id, url, title, extract, **kwargs):
        self.id = id
        self.url = url
        self.title = title
        self.extract = extract

@dataclass
class GetContentsResponse:
    contents: List[DocumentContent]

@dataclass
class SearchResponse:
    results: List[Result]
    api: Optional['Metaphor'] = field(default=None, init=False)

    def get_contents(self):
        if self.api is None:
            raise Exception("API client is not set. This method should be called on a SearchResponse returned by the 'search' method of 'Metaphor'.")
        ids = [result.id for result in self.results]
        return self.api.get_contents(ids)

class Metaphor:
    def __init__(self, api_key: str):
        self.base_url = "https://api.metaphor.systems"
        self.headers = {"x-api-key": api_key}

    def search(self, query: str, **options) -> SearchResponse:
        validate_search_options(options)
        request = {'query': query}
        request.update(to_camel_case(options))
        response = requests.post(f"{self.base_url}/search", json=request, headers=self.headers)
        response.raise_for_status()
        results = [Result(**to_snake_case(result)) for result in response.json()["results"]]
        search_response = SearchResponse(results=results)
        search_response.api = self
        return search_response

    def find_similar(self, url: str, **options) -> SearchResponse:
        validate_find_similar_options(options)
        request = {'url': url}
        request.update(to_camel_case(options))
        response = requests.post(f"{self.base_url}/findSimilar", json=request, headers=self.headers)
        response.raise_for_status()
        results = [Result(**to_snake_case(result)) for result in response.json()["results"]]
        find_similar_response = SearchResponse(results=results)
        find_similar_response.api = self
        return find_similar_response

    def get_contents(self, ids: List[str]) -> GetContentsResponse:
        response = requests.get(f"{self.base_url}/contents", params=to_camel_case({"ids": ids}), headers=self.headers)
        response.raise_for_status()
        return GetContentsResponse([DocumentContent(**to_snake_case(document)) for document in response.json()["contents"]])
