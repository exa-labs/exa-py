import re
import requests
from typing import List, Optional
from dataclasses import dataclass

def snake_to_camel(snake_str: str) -> str:
    components = snake_str.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])

def to_camel_case(data: dict) -> dict:
    return {snake_to_camel(k): v for k, v in data.items() if v is not None}

def camel_to_snake(camel_str: str) -> str:
    snake_str = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', camel_str)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', snake_str).lower()

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

@dataclass
class Result:
    title: str
    url: str
    score: float
    id: str
    published_date: Optional[str] = None
    author: Optional[str] = None

@dataclass
class SearchResponse:
    results: List[Result]

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
    url: str
    title: str
    extract: str

@dataclass
class GetContentsResponse:
    contents: List[DocumentContent]

class Metaphor:
    def __init__(self, api_key: str):
        self.base_url = 'https://api.metaphor.systems'
        self.headers = {'x-api-key': api_key}

    def search(self, request: SearchRequest) -> SearchResponse:
        response = requests.post(f'{self.base_url}/search', json=to_camel_case(request.__dict__), headers=self.headers)
        response.raise_for_status()
        return SearchResponse([Result(**to_snake_case(result)) for result in response.json()['results']])

    def find_similar(self, request: FindSimilarRequest) -> SearchResponse:
        response = requests.post(f'{self.base_url}/findSimilar', json=to_camel_case(request.__dict__), headers=self.headers)
        response.raise_for_status()
        return SearchResponse([Result(**to_snake_case(result)) for result in response.json()['results']])

    def get_contents(self, request: GetContentsRequest) -> GetContentsResponse:
        response = requests.get(f'{self.base_url}/contents', params=to_camel_case(request.__dict__), headers=self.headers)
        response.raise_for_status()
        return GetContentsResponse([DocumentContent(**to_snake_case(document)) for document in response.json()['contents']])
