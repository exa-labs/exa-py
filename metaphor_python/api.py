import re
import requests
from typing import List, Optional
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

@dataclass
class SearchRequest:
    query: str
    num_results: Optional[int] = None
    include_domains: Optional[List[str]] = None
    exclude_domains: Optional[List[str]] = None
    start_crawl_date: Optional[str] = None
    end_crawl_date: Optional[str] = None
    start_published_date: Optional[str] = None
    end_published_date: Optional[str] = None
    use_autoprompt: Optional[bool] = None
    type: Optional[str] = None # keyword or neural. Default is neural.

@dataclass
class Result:
    title: str
    url: str
    score: float
    id: str
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
class FindSimilarRequest:
    url: str
    num_results: Optional[int] = None
    include_domains: Optional[List[str]] = None
    exclude_domains: Optional[List[str]] = None
    start_crawl_date: Optional[str] = None
    end_crawl_date: Optional[str] = None
    start_published_date: Optional[str] = None
    end_published_date: Optional[str] = None

@dataclass
class GetContentsRequest:
    ids: List[str]

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
        get_contents_request = GetContentsRequest(ids=ids)
        return self.api.get_contents(get_contents_request)

class Metaphor:
    def __init__(self, api_key: str):
        self.base_url = "https://api.metaphor.systems"
        self.headers = {"x-api-key": api_key}

    def search(self, request: SearchRequest) -> SearchResponse:
        response = requests.post(f"{self.base_url}/search", json=to_camel_case(request.__dict__), headers=self.headers)
        response.raise_for_status()
        results = [Result(**to_snake_case(result)) for result in response.json()["results"]]
        search_response = SearchResponse(results=results)
        search_response.api = self
        return search_response

    def find_similar(self, request: FindSimilarRequest) -> SearchResponse:
        response = requests.post(f"{self.base_url}/findSimilar", json=to_camel_case(request.__dict__), headers=self.headers)
        response.raise_for_status()
        results = [Result(**to_snake_case(result)) for result in response.json()["results"]]
        find_similar_response = SearchResponse(results=results)
        find_similar_response.api = self
        return find_similar_response

    def get_contents(self, request: GetContentsRequest) -> GetContentsResponse:
        response = requests.get(f"{self.base_url}/contents", params=to_camel_case(request.__dict__), headers=self.headers)
        response.raise_for_status()
        return GetContentsResponse([DocumentContent(**to_snake_case(document)) for document in response.json()["contents"]])
