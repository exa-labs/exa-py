from __future__ import annotations
from dataclasses import dataclass
import dataclasses
from functools import wraps
import re
import requests
from typing import (
    Callable,
    Iterable,
    List,
    Optional,
    Dict,
    Generic,
    TypeVar,
    overload,
    Union,
    Literal,
    get_origin,
    get_args,
)
from typing_extensions import TypedDict

from openai import OpenAI
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
from openai.types.chat_model import ChatModel
from exa_py.utils import (
    ExaOpenAICompletion,
    add_message_to_messages,
    format_exa_result,
    maybe_get_query,
)
import os
from typing import Iterator

is_beta = os.getenv("IS_BETA") == "True"


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
    """
    Convert keys in a dictionary from snake_case to camelCase recursively.

    Args:
        data (dict): The dictionary with keys in snake_case format.

    Returns:
        dict: The dictionary with keys converted to camelCase format.
    """
    if isinstance(data, dict):
        return {
            snake_to_camel(k): to_camel_case(v) if isinstance(v, dict) else v
            for k, v in data.items()
            if v is not None
        }
    return data


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
    """
    Convert keys in a dictionary from camelCase to snake_case recursively.

    Args:
        data (dict): The dictionary with keys in camelCase format.

    Returns:
        dict: The dictionary with keys converted to snake_case format.
    """
    if isinstance(data, dict):
        return {
            camel_to_snake(k): to_snake_case(v) if isinstance(v, dict) else v
            for k, v in data.items()
        }
    return data


SEARCH_OPTIONS_TYPES = {
    "query": [str],  # The query string.
    "num_results": [int],  # Number of results (Default: 10, Max for basic: 10).
    "include_domains": [list],  # Domains to search from; exclusive with 'exclude_domains'.
    "exclude_domains": [list],  # Domains to omit; exclusive with 'include_domains'.
    "start_crawl_date": [str],  # Results after this crawl date. ISO 8601 format.
    "end_crawl_date": [str],  # Results before this crawl date. ISO 8601 format.
    "start_published_date": [str],  # Results after this publish date; excludes links with no date. ISO 8601 format.
    "end_published_date": [str],  # Results before this publish date; excludes links with no date. ISO 8601 format.
    "include_text": [list],  # Must be present in webpage text. (One string, up to 5 words)
    "exclude_text": [list],  # Must not be present in webpage text. (One string, up to 5 words)
    "use_autoprompt": [bool],  # Convert query to Exa. (Default: false)
    "type": [str],  # 'keyword', 'neural', or 'auto' (Default: auto)
    "category": [str],  # A data category to focus on: 'company', 'research paper', 'news', 'pdf', 'github', 'tweet', 'personal site', 'linkedin profile', 'financial report'
    "flags": [list],  # Experimental flags array for Exa usage.
    "moderation": [bool],  # If true, moderate search results for safety.
}

FIND_SIMILAR_OPTIONS_TYPES = {
    "url": [str],
    "num_results": [int],
    "include_domains": [list],
    "exclude_domains": [list],
    "start_crawl_date": [str],
    "end_crawl_date": [str],
    "start_published_date": [str],
    "end_published_date": [str],
    "include_text": [list],
    "exclude_text": [list],
    "exclude_source_domain": [bool],
    "category": [str],
    "flags": [list],  # Experimental flags array for Exa usage.
}

# the livecrawl options
LIVECRAWL_OPTIONS = Literal["always", "fallback", "never", "auto"]

CONTENTS_OPTIONS_TYPES = {
    "urls": [list],
    "text": [dict, bool],
    "highlights": [dict, bool],
    "summary": [dict, bool],
    "metadata": [dict, bool],
    "livecrawl_timeout": [int],
    "livecrawl": [LIVECRAWL_OPTIONS],
    "filter_empty_results": [bool],
    "flags": [list],  # We allow flags to be passed here too
}

CONTENTS_ENDPOINT_OPTIONS_TYPES = {
    "subpages": [int],
    "subpage_target": [str, list],
    "extras": [dict],
    "flags": [list],  # We allow flags to be passed here too
}


def validate_search_options(
    options: Dict[str, Optional[object]], expected: dict
) -> None:
    """Validate an options dict against expected types and constraints.

    Args:
        options (Dict[str, Optional[object]]): The options to validate.
        expected (dict): The expected types for each option.

    Raises:
        ValueError: If an invalid option or option type is provided.
    """
    for key, value in options.items():
        if key not in expected:
            raise ValueError(f"Invalid option: '{key}'")
        if value is None:
            continue
        expected_types = expected[key]
        if not any(is_valid_type(value, t) for t in expected_types):
            raise ValueError(
                f"Invalid value for option '{key}': {value}. Expected one of {expected_types}"
            )


def is_valid_type(value, expected_type):
    if get_origin(expected_type) is Literal:
        return value in get_args(expected_type)
    if isinstance(expected_type, type):
        return isinstance(value, expected_type)
    return False  # For any other case


class TextContentsOptions(TypedDict, total=False):
    """A class representing the options that you can specify when requesting text

    Attributes:
        max_characters (int): The maximum number of characters to return. Default: None (no limit).
        include_html_tags (bool): If true, include HTML tags in the returned text. Default false.
    """

    max_characters: int
    include_html_tags: bool


class HighlightsContentsOptions(TypedDict, total=False):
    """A class representing the options that you can specify when requesting highlights

    Attributes:
        query (str): The query string for the highlights.
        num_sentences (int): Size of highlights to return, in sentences. Default: 5
        highlights_per_url (int): Number of highlights to return per URL. Default: 1
    """

    query: str
    num_sentences: int
    highlights_per_url: int


class SummaryContentsOptions(TypedDict, total=False):
    """A class representing the options that you can specify when requesting summary

    Attributes:
        query (str): The query string for the summary. Summary will bias towards answering the query.
    """

    query: str


class ExtrasOptions(TypedDict, total=False):
    """A class representing additional extraction fields (e.g. links, images)"""

    links: int
    image_links: int


@dataclass
class _Result:
    """A class representing the base fields of a search result.

    Attributes:
        title (str): The title of the search result.
        url (str): The URL of the search result.
        id (str): The temporary ID for the document.
        score (float, optional): A number from 0 to 1 representing similarity.
        published_date (str, optional): An estimate of the creation date, from parsing HTML content.
        author (str, optional): The author of the content (if available).
        image (str, optional): A URL to an image associated with the content (if available).
        favicon (str, optional): A URL to the favicon (if available).
        subpages (List[_Result], optional): Subpages of main page
        extras (Dict, optional): Additional metadata; e.g. links, images.
    """

    url: str
    id: str
    title: Optional[str] = None
    score: Optional[float] = None
    published_date: Optional[str] = None
    author: Optional[str] = None
    image: Optional[str] = None
    favicon: Optional[str] = None
    subpages: Optional[List[_Result]] = None
    extras: Optional[Dict] = None

    def __init__(self, **kwargs):
        self.url = kwargs["url"]
        self.id = kwargs["id"]
        self.title = kwargs.get("title")
        self.score = kwargs.get("score")
        self.published_date = kwargs.get("published_date")
        self.author = kwargs.get("author")
        self.image = kwargs.get("image")
        self.favicon = kwargs.get("favicon")
        self.subpages = kwargs.get("subpages")
        self.extras = kwargs.get("extras")

    def __str__(self):
        return (
            f"Title: {self.title}\n"
            f"URL: {self.url}\n"
            f"ID: {self.id}\n"
            f"Score: {self.score}\n"
            f"Published Date: {self.published_date}\n"
            f"Author: {self.author}\n"
            f"Image: {self.image}\n"
            f"Favicon: {self.favicon}\n"
            f"Extras: {self.extras}\n"
            f"Subpages: {self.subpages}\n"
        )


@dataclass
class Result(_Result):
    """
    A class representing a search result with optional text, highlights, summary.

    Attributes:
        text (str, optional)
        highlights (List[str], optional)
        highlight_scores (List[float], optional)
        summary (str, optional)
    """

    text: Optional[str] = None
    highlights: Optional[List[str]] = None
    highlight_scores: Optional[List[float]] = None
    summary: Optional[str] = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.text = kwargs.get("text")
        self.highlights = kwargs.get("highlights")
        self.highlight_scores = kwargs.get("highlight_scores")
        self.summary = kwargs.get("summary")

    def __str__(self):
        base_str = super().__str__()
        return base_str + (
            f"Text: {self.text}\n"
            f"Highlights: {self.highlights}\n"
            f"Highlight Scores: {self.highlight_scores}\n"
            f"Summary: {self.summary}\n"
        )


@dataclass
class ResultWithText(_Result):
    """
    A class representing a search result with text present.

    Attributes:
        text (str): The text of the search result page.
    """

    text: str = dataclasses.field(default_factory=str)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.text = kwargs["text"]

    def __str__(self):
        base_str = super().__str__()
        return base_str + f"Text: {self.text}\n"


@dataclass
class ResultWithHighlights(_Result):
    """
    A class representing a search result with highlights present.

    Attributes:
        highlights (List[str])
        highlight_scores (List[float])
    """

    highlights: List[str] = dataclasses.field(default_factory=list)
    highlight_scores: List[float] = dataclasses.field(default_factory=list)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.highlights = kwargs["highlights"]
        self.highlight_scores = kwargs["highlight_scores"]

    def __str__(self):
        base_str = super().__str__()
        return base_str + (
            f"Highlights: {self.highlights}\n"
            f"Highlight Scores: {self.highlight_scores}\n"
        )


@dataclass
class ResultWithTextAndHighlights(_Result):
    """
    A class representing a search result with text and highlights present.

    Attributes:
        text (str)
        highlights (List[str])
        highlight_scores (List[float])
    """

    text: str = dataclasses.field(default_factory=str)
    highlights: List[str] = dataclasses.field(default_factory=list)
    highlight_scores: List[float] = dataclasses.field(default_factory=list)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.text = kwargs["text"]
        self.highlights = kwargs["highlights"]
        self.highlight_scores = kwargs["highlight_scores"]

    def __str__(self):
        base_str = super().__str__()
        return base_str + (
            f"Text: {self.text}\n"
            f"Highlights: {self.highlights}\n"
            f"Highlight Scores: {self.highlight_scores}\n"
        )


@dataclass
class ResultWithSummary(_Result):
    """
    A class representing a search result with summary present.

    Attributes:
        summary (str)
    """

    summary: str = dataclasses.field(default_factory=str)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.summary = kwargs["summary"]

    def __str__(self):
        base_str = super().__str__()
        return base_str + f"Summary: {self.summary}\n"


@dataclass
class ResultWithTextAndSummary(_Result):
    """
    A class representing a search result with text and summary present.

    Attributes:
        text (str)
        summary (str)
    """

    text: str = dataclasses.field(default_factory=str)
    summary: str = dataclasses.field(default_factory=str)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.text = kwargs["text"]
        self.summary = kwargs["summary"]

    def __str__(self):
        base_str = super().__str__()
        return base_str + f"Text: {self.text}\n" + f"Summary: {self.summary}\n"


@dataclass
class ResultWithHighlightsAndSummary(_Result):
    """
    A class representing a search result with highlights and summary present.

    Attributes:
        highlights (List[str])
        highlight_scores (List[float])
        summary (str)
    """

    highlights: List[str] = dataclasses.field(default_factory=list)
    highlight_scores: List[float] = dataclasses.field(default_factory=list)
    summary: str = dataclasses.field(default_factory=str)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.highlights = kwargs["highlights"]
        self.highlight_scores = kwargs["highlight_scores"]
        self.summary = kwargs["summary"]

    def __str__(self):
        base_str = super().__str__()
        return base_str + (
            f"Highlights: {self.highlights}\n"
            f"Highlight Scores: {self.highlight_scores}\n"
            f"Summary: {self.summary}\n"
        )


@dataclass
class ResultWithTextAndHighlightsAndSummary(_Result):
    """
    A class representing a search result with text, highlights, and summary present.

    Attributes:
        text (str)
        highlights (List[str])
        highlight_scores (List[float])
        summary (str)
    """

    text: str = dataclasses.field(default_factory=str)
    highlights: List[str] = dataclasses.field(default_factory=list)
    highlight_scores: List[float] = dataclasses.field(default_factory=list)
    summary: str = dataclasses.field(default_factory=str)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.text = kwargs["text"]
        self.highlights = kwargs["highlights"]
        self.highlight_scores = kwargs["highlight_scores"]
        self.summary = kwargs["summary"]

    def __str__(self):
        base_str = super().__str__()
        return base_str + (
            f"Text: {self.text}\n"
            f"Highlights: {self.highlights}\n"
            f"Highlight Scores: {self.highlight_scores}\n"
            f"Summary: {self.summary}\n"
        )


@dataclass
class AnswerResult:
    """A class representing a source result for an answer.

    Attributes:
        title (str): The title of the search result.
        url (str): The URL of the search result.
        id (str): The temporary ID for the document.
        published_date (str, optional): An estimate of the creation date, from parsing HTML content.
        author (str, optional): If available, the author of the content.
    """

    url: str
    id: str
    title: Optional[str] = None
    published_date: Optional[str] = None
    author: Optional[str] = None

    def __init__(self, **kwargs):
        self.url = kwargs["url"]
        self.id = kwargs["id"]
        self.title = kwargs.get("title")
        self.published_date = kwargs.get("published_date")
        self.author = kwargs.get("author")

    def __str__(self):
        return (
            f"Title: {self.title}\n"
            f"URL: {self.url}\n"
            f"ID: {self.id}\n"
            f"Published Date: {self.published_date}\n"
            f"Author: {self.author}\n"
        )


@dataclass
class AnswerResponse:
    """A class representing the response for an answer operation.

    Attributes:
        answer (str): The generated answer.
        sources (List[AnswerResult]): A list of sources used to generate the answer.
    """

    answer: str
    sources: List[AnswerResult]

    def __str__(self):
        output = f"Answer: {self.answer}\n\nSources:\n"
        output += "\n\n".join(str(source) for source in self.sources)
        return output


T = TypeVar("T")


@dataclass
class SearchResponse(Generic[T]):
    """A class representing the response for a search operation.

    Attributes:
        results (List[Result]): A list of search results.
        autoprompt_string (str, optional): The Exa query created by autoprompt.
        resolved_search_type (str, optional): 'neural' or 'keyword' if auto.
        auto_date (str, optional): A date for filtering if autoprompt found one.
    """

    results: List[T]
    autoprompt_string: Optional[str]
    resolved_search_type: Optional[str]
    auto_date: Optional[str]

    def __str__(self):
        output = "\n\n".join(str(result) for result in self.results)
        if self.autoprompt_string:
            output += f"\n\nAutoprompt String: {self.autoprompt_string}"
        if self.resolved_search_type:
            output += f"\nResolved Search Type: {self.resolved_search_type}"

        return output


def nest_fields(original_dict: Dict, fields_to_nest: List[str], new_key: str):
    # Create a new dictionary to store the nested fields
    nested_dict = {}

    # Iterate over the fields to be nested
    for field in fields_to_nest:
        # Check if the field exists in the original dictionary
        if field in original_dict:
            # Move the field to the nested dictionary
            nested_dict[field] = original_dict.pop(field)

    # Add the nested dictionary to the original dictionary under the new key
    original_dict[new_key] = nested_dict

    return original_dict


class Exa:
    """A client for interacting with Exa API."""

    def __init__(
        self,
        api_key: Optional[str],
        base_url: str = "https://api.exa.ai",
        user_agent: str = "exa-py 1.8.4",
    ):
        """Initialize the Exa client with the provided API key and optional base URL and user agent.

        Args:
            api_key (str): The API key for authenticating with the Exa API.
            base_url (str, optional): The base URL for the Exa API. Defaults to "https://api.exa.ai".
        """
        if api_key is None:
            import os

            api_key = os.environ.get("EXA_API_KEY")
            if api_key is None:
                raise ValueError(
                    "API key must be provided as an argument or in EXA_API_KEY environment variable"
                )
        self.base_url = base_url
        self.headers = {"x-api-key": api_key, "User-Agent": user_agent}

    def request(self, endpoint: str, data):
        """Send a POST request to the Exa API, optionally streaming if data['stream'] is True.

        Args:
            endpoint (str): The API endpoint (path).
            data (dict): The JSON payload to send.

        Returns:
            Union[dict, Iterator[str]]: If streaming, returns an iterator of strings (line-by-line).
            Otherwise, returns the JSON-decoded response as a dict.

        Raises:
            ValueError: If the request fails (non-200 status code).
        """
        if data.get("stream"):
            res = requests.post(self.base_url + endpoint, json=data, headers=self.headers, stream=True)
            if res.status_code != 200:
                raise ValueError(f"Request failed with status code {res.status_code}: {res.text}")
            return (line.decode("utf-8") for line in res.iter_lines() if line)

        res = requests.post(self.base_url + endpoint, json=data, headers=self.headers)
        if res.status_code != 200:
            raise ValueError(f"Request failed with status code {res.status_code}: {res.text}")
        return res.json()

    def search(
        self,
        query: str,
        *,
        num_results: Optional[int] = None,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        start_crawl_date: Optional[str] = None,
        end_crawl_date: Optional[str] = None,
        start_published_date: Optional[str] = None,
        end_published_date: Optional[str] = None,
        include_text: Optional[List[str]] = None,
        exclude_text: Optional[List[str]] = None,
        use_autoprompt: Optional[bool] = None,
        type: Optional[str] = None,
        category: Optional[str] = None,
        flags: Optional[List[str]] = None,
        moderation: Optional[bool] = None,
    ) -> SearchResponse[_Result]:
        """Perform a search with a prompt-engineered query to retrieve relevant results.

        Args:
            query (str): The query string.
            num_results (int, optional): Number of search results to return (default 10).
            include_domains (List[str], optional): Domains to include in the search.
            exclude_domains (List[str], optional): Domains to exclude from the search.
            start_crawl_date (str, optional): Only links crawled after this date.
            end_crawl_date (str, optional): Only links crawled before this date.
            start_published_date (str, optional): Only links published after this date.
            end_published_date (str, optional): Only links published before this date.
            include_text (List[str], optional): Strings that must appear in the page text.
            exclude_text (List[str], optional): Strings that must not appear in the page text.
            use_autoprompt (bool, optional): Convert query to Exa (default False).
            type (str, optional): 'keyword' or 'neural' (default 'neural').
            category (str, optional): e.g. 'company'
            flags (List[str], optional): Experimental flags for Exa usage.
            moderation (bool, optional): If True, the search results will be moderated for safety.

        Returns:
            SearchResponse: The response containing search results, etc.
        """
        options = {k: v for k, v in locals().items() if k != "self" and v is not None}
        validate_search_options(options, SEARCH_OPTIONS_TYPES)
        options = to_camel_case(options)
        data = self.request("/search", options)
        return SearchResponse(
            [Result(**to_snake_case(result)) for result in data["results"]],
            data["autopromptString"] if "autopromptString" in data else None,
            data["resolvedSearchType"] if "resolvedSearchType" in data else None,
            data["autoDate"] if "autoDate" in data else None,
        )

    @overload
    def search_and_contents(
        self,
        query: str,
        *,
        num_results: Optional[int] = None,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        start_crawl_date: Optional[str] = None,
        end_crawl_date: Optional[str] = None,
        start_published_date: Optional[str] = None,
        end_published_date: Optional[str] = None,
        include_text: Optional[List[str]] = None,
        exclude_text: Optional[List[str]] = None,
        use_autoprompt: Optional[bool] = None,
        type: Optional[str] = None,
        category: Optional[str] = None,
        flags: Optional[List[str]] = None,
        moderation: Optional[bool] = None,
        livecrawl_timeout: Optional[int] = None,
        livecrawl: Optional[LIVECRAWL_OPTIONS] = None,
        filter_empty_results: Optional[bool] = None,
        subpages: Optional[int] = None,
        extras: Optional[ExtrasOptions] = None,
    ) -> SearchResponse[ResultWithText]:
        ...

    @overload
    def search_and_contents(
        self,
        query: str,
        *,
        text: Union[TextContentsOptions, Literal[True]],
        num_results: Optional[int] = None,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        start_crawl_date: Optional[str] = None,
        end_crawl_date: Optional[str] = None,
        start_published_date: Optional[str] = None,
        end_published_date: Optional[str] = None,
        include_text: Optional[List[str]] = None,
        exclude_text: Optional[List[str]] = None,
        use_autoprompt: Optional[bool] = None,
        type: Optional[str] = None,
        category: Optional[str] = None,
        flags: Optional[List[str]] = None,
        moderation: Optional[bool] = None,
        subpages: Optional[int] = None,
        livecrawl_timeout: Optional[int] = None,
        livecrawl: Optional[LIVECRAWL_OPTIONS] = None,
        filter_empty_results: Optional[bool] = None,
        extras: Optional[ExtrasOptions] = None,
    ) -> SearchResponse[ResultWithText]:
        ...

    @overload
    def search_and_contents(
        self,
        query: str,
        *,
        highlights: Union[HighlightsContentsOptions, Literal[True]],
        num_results: Optional[int] = None,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        start_crawl_date: Optional[str] = None,
        end_crawl_date: Optional[str] = None,
        start_published_date: Optional[str] = None,
        end_published_date: Optional[str] = None,
        include_text: Optional[List[str]] = None,
        exclude_text: Optional[List[str]] = None,
        use_autoprompt: Optional[bool] = None,
        type: Optional[str] = None,
        category: Optional[str] = None,
        subpages: Optional[int] = None,
        subpage_target: Optional[Union[str, List[str]]] = None,
        flags: Optional[List[str]] = None,
        moderation: Optional[bool] = None,
        livecrawl_timeout: Optional[int] = None,
        livecrawl: Optional[LIVECRAWL_OPTIONS] = None,
        filter_empty_results: Optional[bool] = None,
        extras: Optional[ExtrasOptions] = None,
    ) -> SearchResponse[ResultWithHighlights]:
        ...

    @overload
    def search_and_contents(
        self,
        query: str,
        *,
        text: Union[TextContentsOptions, Literal[True]],
        highlights: Union[HighlightsContentsOptions, Literal[True]],
        num_results: Optional[int] = None,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        start_crawl_date: Optional[str] = None,
        end_crawl_date: Optional[str] = None,
        start_published_date: Optional[str] = None,
        end_published_date: Optional[str] = None,
        include_text: Optional[List[str]] = None,
        exclude_text: Optional[List[str]] = None,
        use_autoprompt: Optional[bool] = None,
        type: Optional[str] = None,
        category: Optional[str] = None,
        subpages: Optional[int] = None,
        subpage_target: Optional[Union[str, List[str]]] = None,
        flags: Optional[List[str]] = None,
        moderation: Optional[bool] = None,
        livecrawl_timeout: Optional[int] = None,
        livecrawl: Optional[LIVECRAWL_OPTIONS] = None,
        filter_empty_results: Optional[bool] = None,
        extras: Optional[ExtrasOptions] = None,
    ) -> SearchResponse[ResultWithTextAndHighlights]:
        ...

    @overload
    def search_and_contents(
        self,
        query: str,
        *,
        summary: Union[SummaryContentsOptions, Literal[True]],
        num_results: Optional[int] = None,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        start_crawl_date: Optional[str] = None,
        end_crawl_date: Optional[str] = None,
        start_published_date: Optional[str] = None,
        end_published_date: Optional[str] = None,
        include_text: Optional[List[str]] = None,
        exclude_text: Optional[List[str]] = None,
        use_autoprompt: Optional[bool] = None,
        type: Optional[str] = None,
        category: Optional[str] = None,
        subpages: Optional[int] = None,
        subpage_target: Optional[Union[str, List[str]]] = None,
        flags: Optional[List[str]] = None,
        moderation: Optional[bool] = None,
        livecrawl_timeout: Optional[int] = None,
        livecrawl: Optional[LIVECRAWL_OPTIONS] = None,
        filter_empty_results: Optional[bool] = None,
        extras: Optional[ExtrasOptions] = None,
    ) -> SearchResponse[ResultWithSummary]:
        ...

    @overload
    def search_and_contents(
        self,
        query: str,
        *,
        text: Union[TextContentsOptions, Literal[True]],
        summary: Union[SummaryContentsOptions, Literal[True]],
        num_results: Optional[int] = None,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        start_crawl_date: Optional[str] = None,
        end_crawl_date: Optional[str] = None,
        start_published_date: Optional[str] = None,
        end_published_date: Optional[str] = None,
        include_text: Optional[List[str]] = None,
        exclude_text: Optional[List[str]] = None,
        use_autoprompt: Optional[bool] = None,
        type: Optional[str] = None,
        category: Optional[str] = None,
        subpages: Optional[int] = None,
        subpage_target: Optional[Union[str, List[str]]] = None,
        flags: Optional[List[str]] = None,
        moderation: Optional[bool] = None,
        livecrawl_timeout: Optional[int] = None,
        livecrawl: Optional[LIVECRAWL_OPTIONS] = None,
        filter_empty_results: Optional[bool] = None,
        extras: Optional[ExtrasOptions] = None,
    ) -> SearchResponse[ResultWithTextAndSummary]:
        ...

    @overload
    def search_and_contents(
        self,
        query: str,
        *,
        highlights: Union[HighlightsContentsOptions, Literal[True]],
        summary: Union[SummaryContentsOptions, Literal[True]],
        num_results: Optional[int] = None,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        start_crawl_date: Optional[str] = None,
        end_crawl_date: Optional[str] = None,
        start_published_date: Optional[str] = None,
        end_published_date: Optional[str] = None,
        include_text: Optional[List[str]] = None,
        exclude_text: Optional[List[str]] = None,
        use_autoprompt: Optional[bool] = None,
        type: Optional[str] = None,
        category: Optional[str] = None,
        subpages: Optional[int] = None,
        subpage_target: Optional[Union[str, List[str]]] = None,
        flags: Optional[List[str]] = None,
        moderation: Optional[bool] = None,
        livecrawl_timeout: Optional[int] = None,
        livecrawl: Optional[LIVECRAWL_OPTIONS] = None,
        filter_empty_results: Optional[bool] = None,
        extras: Optional[ExtrasOptions] = None,
    ) -> SearchResponse[ResultWithHighlightsAndSummary]:
        ...

    @overload
    def search_and_contents(
        self,
        query: str,
        *,
        text: Union[TextContentsOptions, Literal[True]],
        highlights: Union[HighlightsContentsOptions, Literal[True]],
        summary: Union[SummaryContentsOptions, Literal[True]],
        num_results: Optional[int] = None,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        start_crawl_date: Optional[str] = None,
        end_crawl_date: Optional[str] = None,
        start_published_date: Optional[str] = None,
        end_published_date: Optional[str] = None,
        include_text: Optional[List[str]] = None,
        exclude_text: Optional[List[str]] = None,
        use_autoprompt: Optional[bool] = None,
        type: Optional[str] = None,
        category: Optional[str] = None,
        flags: Optional[List[str]] = None,
        moderation: Optional[bool] = None,
        livecrawl_timeout: Optional[int] = None,
        livecrawl: Optional[LIVECRAWL_OPTIONS] = None,
        subpages: Optional[int] = None,
        subpage_target: Optional[Union[str, List[str]]] = None,
        filter_empty_results: Optional[bool] = None,
        extras: Optional[ExtrasOptions] = None,
    ) -> SearchResponse[ResultWithTextAndHighlightsAndSummary]:
        ...

    def search_and_contents(self, query: str, **kwargs):
        options = {k: v for k, v in {"query": query, **kwargs}.items() if v is not None}
        # If user didn't ask for any particular content, default to text
        if (
            "text" not in options
            and "highlights" not in options
            and "summary" not in options
            and "extras" not in options
        ):
            options["text"] = True

        validate_search_options(
            options,
            {
                **SEARCH_OPTIONS_TYPES,
                **CONTENTS_OPTIONS_TYPES,
                **CONTENTS_ENDPOINT_OPTIONS_TYPES,
            },
        )

        # Nest the appropriate fields under "contents"
        options = nest_fields(
            options,
            [
                "text",
                "highlights",
                "summary",
                "subpages",
                "subpage_target",
                "livecrawl",
                "livecrawl_timeout",
                "extras",
            ],
            "contents",
        )
        options = to_camel_case(options)
        data = self.request("/search", options)
        return SearchResponse(
            [Result(**to_snake_case(result)) for result in data["results"]],
            data["autopromptString"] if "autopromptString" in data else None,
            data["resolvedSearchType"] if "resolvedSearchType" in data else None,
            data["autoDate"] if "autoDate" in data else None,
        )

    @overload
    def get_contents(
        self,
        urls: Union[str, List[str], List[_Result]],
        livecrawl_timeout: Optional[int] = None,
        livecrawl: Optional[LIVECRAWL_OPTIONS] = None,
        filter_empty_results: Optional[bool] = None,
        subpages: Optional[int] = None,
        subpage_target: Optional[Union[str, List[str]]] = None,
        extras: Optional[ExtrasOptions] = None,
        flags: Optional[List[str]] = None,
    ) -> SearchResponse[ResultWithText]:
        ...

    @overload
    def get_contents(
        self,
        urls: Union[str, List[str], List[_Result]],
        *,
        text: Union[TextContentsOptions, Literal[True]],
        livecrawl_timeout: Optional[int] = None,
        livecrawl: Optional[LIVECRAWL_OPTIONS] = None,
        filter_empty_results: Optional[bool] = None,
        subpages: Optional[int] = None,
        subpage_target: Optional[Union[str, List[str]]] = None,
        extras: Optional[ExtrasOptions] = None,
        flags: Optional[List[str]] = None,
    ) -> SearchResponse[ResultWithText]:
        ...

    @overload
    def get_contents(
        self,
        urls: Union[str, List[str], List[_Result]],
        *,
        highlights: Union[HighlightsContentsOptions, Literal[True]],
        livecrawl_timeout: Optional[int] = None,
        livecrawl: Optional[LIVECRAWL_OPTIONS] = None,
        filter_empty_results: Optional[bool] = None,
        subpages: Optional[int] = None,
        subpage_target: Optional[Union[str, List[str]]] = None,
        extras: Optional[ExtrasOptions] = None,
        flags: Optional[List[str]] = None,
    ) -> SearchResponse[ResultWithHighlights]:
        ...

    @overload
    def get_contents(
        self,
        urls: Union[str, List[str], List[_Result]],
        *,
        text: Union[TextContentsOptions, Literal[True]],
        highlights: Union[HighlightsContentsOptions, Literal[True]],
        livecrawl_timeout: Optional[int] = None,
        livecrawl: Optional[LIVECRAWL_OPTIONS] = None,
        filter_empty_results: Optional[bool] = None,
        subpages: Optional[int] = None,
        subpage_target: Optional[Union[str, List[str]]] = None,
        extras: Optional[ExtrasOptions] = None,
        flags: Optional[List[str]] = None,
    ) -> SearchResponse[ResultWithTextAndHighlights]:
        ...

    @overload
    def get_contents(
        self,
        urls: Union[str, List[str], List[_Result]],
        *,
        summary: Union[SummaryContentsOptions, Literal[True]],
        livecrawl_timeout: Optional[int] = None,
        livecrawl: Optional[LIVECRAWL_OPTIONS] = None,
        filter_empty_results: Optional[bool] = None,
        subpages: Optional[int] = None,
        subpage_target: Optional[Union[str, List[str]]] = None,
        extras: Optional[ExtrasOptions] = None,
        flags: Optional[List[str]] = None,
    ) -> SearchResponse[ResultWithSummary]:
        ...

    @overload
    def get_contents(
        self,
        urls: Union[str, List[str], List[_Result]],
        *,
        text: Union[TextContentsOptions, Literal[True]],
        summary: Union[SummaryContentsOptions, Literal[True]],
        livecrawl_timeout: Optional[int] = None,
        livecrawl: Optional[LIVECRAWL_OPTIONS] = None,
        filter_empty_results: Optional[bool] = None,
        subpages: Optional[int] = None,
        subpage_target: Optional[Union[str, List[str]]] = None,
        extras: Optional[ExtrasOptions] = None,
        flags: Optional[List[str]] = None,
    ) -> SearchResponse[ResultWithTextAndSummary]:
        ...

    @overload
    def get_contents(
        self,
        urls: Union[str, List[str], List[_Result]],
        *,
        highlights: Union[HighlightsContentsOptions, Literal[True]],
        summary: Union[SummaryContentsOptions, Literal[True]],
        livecrawl_timeout: Optional[int] = None,
        livecrawl: Optional[LIVECRAWL_OPTIONS] = None,
        filter_empty_results: Optional[bool] = None,
        subpages: Optional[int] = None,
        subpage_target: Optional[Union[str, List[str]]] = None,
        extras: Optional[ExtrasOptions] = None,
        flags: Optional[List[str]] = None,
    ) -> SearchResponse[ResultWithHighlightsAndSummary]:
        ...

    @overload
    def get_contents(
        self,
        urls: Union[str, List[str], List[_Result]],
        *,
        text: Union[TextContentsOptions, Literal[True]],
        highlights: Union[HighlightsContentsOptions, Literal[True]],
        summary: Union[SummaryContentsOptions, Literal[True]],
        livecrawl_timeout: Optional[int] = None,
        livecrawl: Optional[LIVECRAWL_OPTIONS] = None,
        filter_empty_results: Optional[bool] = None,
        subpages: Optional[int] = None,
        subpage_target: Optional[Union[str, List[str]]] = None,
        extras: Optional[ExtrasOptions] = None,
        flags: Optional[List[str]] = None,
    ) -> SearchResponse[ResultWithTextAndHighlightsAndSummary]:
        ...

    def get_contents(self, urls: Union[str, List[str], List[_Result]], **kwargs):
        options = {
            k: v
            for k, v in {"urls": urls, **kwargs}.items()
            if k != "self" and v is not None
        }
        if (
            "text" not in options
            and "highlights" not in options
            and "summary" not in options
            and "extras" not in options
        ):
            options["text"] = True

        validate_search_options(
            options,
            {**CONTENTS_OPTIONS_TYPES, **CONTENTS_ENDPOINT_OPTIONS_TYPES},
        )
        options = to_camel_case(options)
        data = self.request("/contents", options)
        return SearchResponse(
            [Result(**to_snake_case(result)) for result in data["results"]],
            data.get("autopromptString"),
            data.get("resolvedSearchType"),
            data.get("autoDate"),
        )

    def find_similar(
        self,
        url: str,
        *,
        num_results: Optional[int] = None,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        start_crawl_date: Optional[str] = None,
        end_crawl_date: Optional[str] = None,
        start_published_date: Optional[str] = None,
        end_published_date: Optional[str] = None,
        include_text: Optional[List[str]] = None,
        exclude_text: Optional[List[str]] = None,
        exclude_source_domain: Optional[bool] = None,
        category: Optional[str] = None,
        flags: Optional[List[str]] = None,
    ) -> SearchResponse[_Result]:
        """Finds similar pages to a given URL, potentially with domain filters and date filters.

        Args:
            url (str): The URL to find similar pages for.
            num_results (int, optional): Number of results to return. Default is None (server default).
            include_domains (List[str], optional): Domains to include in the search.
            exclude_domains (List[str], optional): Domains to exclude from the search.
            start_crawl_date (str, optional): Only links crawled after this date.
            end_crawl_date (str, optional): Only links crawled before this date.
            start_published_date (str, optional): Only links published after this date.
            end_published_date (str, optional): Only links published before this date.
            include_text (List[str], optional): Strings that must appear in the page text.
            exclude_text (List[str], optional): Strings that must not appear in the page text.
            exclude_source_domain (bool, optional): Whether to exclude the source domain.
            category (str, optional): A data category to focus on.
            flags (List[str], optional): Experimental flags.

        Returns:
            SearchResponse[_Result]
        """
        options = {k: v for k, v in locals().items() if k != "self" and v is not None}
        validate_search_options(options, FIND_SIMILAR_OPTIONS_TYPES)
        options = to_camel_case(options)
        data = self.request("/findSimilar", options)
        return SearchResponse(
            [Result(**to_snake_case(result)) for result in data["results"]],
            data.get("autopromptString"),
            data.get("resolvedSearchType"),
            data.get("autoDate"),
        )

    @overload
    def find_similar_and_contents(
        self,
        url: str,
        *,
        num_results: Optional[int] = None,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        start_crawl_date: Optional[str] = None,
        end_crawl_date: Optional[str] = None,
        start_published_date: Optional[str] = None,
        end_published_date: Optional[str] = None,
        include_text: Optional[List[str]] = None,
        exclude_text: Optional[List[str]] = None,
        exclude_source_domain: Optional[bool] = None,
        category: Optional[str] = None,
        flags: Optional[List[str]] = None,
        livecrawl_timeout: Optional[int] = None,
        livecrawl: Optional[LIVECRAWL_OPTIONS] = None,
        filter_empty_results: Optional[bool] = None,
        subpages: Optional[int] = None,
        subpage_target: Optional[Union[str, List[str]]] = None,
        extras: Optional[ExtrasOptions] = None,
    ) -> SearchResponse[ResultWithText]:
        ...

    @overload
    def find_similar_and_contents(
        self,
        url: str,
        *,
        text: Union[TextContentsOptions, Literal[True]],
        num_results: Optional[int] = None,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        start_crawl_date: Optional[str] = None,
        end_crawl_date: Optional[str] = None,
        start_published_date: Optional[str] = None,
        end_published_date: Optional[str] = None,
        include_text: Optional[List[str]] = None,
        exclude_text: Optional[List[str]] = None,
        exclude_source_domain: Optional[bool] = None,
        category: Optional[str] = None,
        flags: Optional[List[str]] = None,
        livecrawl_timeout: Optional[int] = None,
        livecrawl: Optional[LIVECRAWL_OPTIONS] = None,
        filter_empty_results: Optional[bool] = None,
        subpages: Optional[int] = None,
        subpage_target: Optional[Union[str, List[str]]] = None,
        extras: Optional[ExtrasOptions] = None,
    ) -> SearchResponse[ResultWithText]:
        ...

    @overload
    def find_similar_and_contents(
        self,
        url: str,
        *,
        highlights: Union[HighlightsContentsOptions, Literal[True]],
        num_results: Optional[int] = None,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        start_crawl_date: Optional[str] = None,
        end_crawl_date: Optional[str] = None,
        start_published_date: Optional[str] = None,
        end_published_date: Optional[str] = None,
        include_text: Optional[List[str]] = None,
        exclude_text: Optional[List[str]] = None,
        exclude_source_domain: Optional[bool] = None,
        category: Optional[str] = None,
        flags: Optional[List[str]] = None,
        subpages: Optional[int] = None,
        subpage_target: Optional[Union[str, List[str]]] = None,
        livecrawl_timeout: Optional[int] = None,
        livecrawl: Optional[LIVECRAWL_OPTIONS] = None,
        filter_empty_results: Optional[bool] = None,
        extras: Optional[ExtrasOptions] = None,
    ) -> SearchResponse[ResultWithHighlights]:
        ...

    @overload
    def find_similar_and_contents(
        self,
        url: str,
        *,
        text: Union[TextContentsOptions, Literal[True]],
        highlights: Union[HighlightsContentsOptions, Literal[True]],
        num_results: Optional[int] = None,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        start_crawl_date: Optional[str] = None,
        end_crawl_date: Optional[str] = None,
        start_published_date: Optional[str] = None,
        end_published_date: Optional[str] = None,
        include_text: Optional[List[str]] = None,
        exclude_text: Optional[List[str]] = None,
        exclude_source_domain: Optional[bool] = None,
        category: Optional[str] = None,
        flags: Optional[List[str]] = None,
        livecrawl_timeout: Optional[int] = None,
        livecrawl: Optional[LIVECRAWL_OPTIONS] = None,
        filter_empty_results: Optional[bool] = None,
        subpages: Optional[int] = None,
        subpage_target: Optional[Union[str, List[str]]] = None,
        extras: Optional[ExtrasOptions] = None,
    ) -> SearchResponse[ResultWithTextAndHighlights]:
        ...

    @overload
    def find_similar_and_contents(
        self,
        url: str,
        *,
        summary: Union[SummaryContentsOptions, Literal[True]],
        num_results: Optional[int] = None,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        start_crawl_date: Optional[str] = None,
        end_crawl_date: Optional[str] = None,
        start_published_date: Optional[str] = None,
        end_published_date: Optional[str] = None,
        include_text: Optional[List[str]] = None,
        exclude_text: Optional[List[str]] = None,
        exclude_source_domain: Optional[bool] = None,
        category: Optional[str] = None,
        flags: Optional[List[str]] = None,
        livecrawl_timeout: Optional[int] = None,
        livecrawl: Optional[LIVECRAWL_OPTIONS] = None,
        filter_empty_results: Optional[bool] = None,
        subpages: Optional[int] = None,
        subpage_target: Optional[Union[str, List[str]]] = None,
        extras: Optional[ExtrasOptions] = None,
    ) -> SearchResponse[ResultWithSummary]:
        ...

    @overload
    def find_similar_and_contents(
        self,
        url: str,
        *,
        text: Union[TextContentsOptions, Literal[True]],
        summary: Union[SummaryContentsOptions, Literal[True]],
        num_results: Optional[int] = None,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        start_crawl_date: Optional[str] = None,
        end_crawl_date: Optional[str] = None,
        start_published_date: Optional[str] = None,
        end_published_date: Optional[str] = None,
        include_text: Optional[List[str]] = None,
        exclude_text: Optional[List[str]] = None,
        exclude_source_domain: Optional[bool] = None,
        category: Optional[str] = None,
        flags: Optional[List[str]] = None,
        livecrawl_timeout: Optional[int] = None,
        livecrawl: Optional[LIVECRAWL_OPTIONS] = None,
        filter_empty_results: Optional[bool] = None,
        subpages: Optional[int] = None,
        subpage_target: Optional[Union[str, List[str]]] = None,
        extras: Optional[ExtrasOptions] = None,
    ) -> SearchResponse[ResultWithTextAndSummary]:
        ...

    @overload
    def find_similar_and_contents(
        self,
        url: str,
        *,
        highlights: Union[HighlightsContentsOptions, Literal[True]],
        summary: Union[SummaryContentsOptions, Literal[True]],
        num_results: Optional[int] = None,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        start_crawl_date: Optional[str] = None,
        end_crawl_date: Optional[str] = None,
        start_published_date: Optional[str] = None,
        end_published_date: Optional[str] = None,
        include_text: Optional[List[str]] = None,
        exclude_text: Optional[List[str]] = None,
        exclude_source_domain: Optional[bool] = None,
        category: Optional[str] = None,
        flags: Optional[List[str]] = None,
        subpages: Optional[int] = None,
        subpage_target: Optional[Union[str, List[str]]] = None,
        livecrawl_timeout: Optional[int] = None,
        livecrawl: Optional[LIVECRAWL_OPTIONS] = None,
        filter_empty_results: Optional[bool] = None,
        extras: Optional[ExtrasOptions] = None,
    ) -> SearchResponse[ResultWithHighlightsAndSummary]:
        ...

    @overload
    def find_similar_and_contents(
        self,
        url: str,
        *,
        text: Union[TextContentsOptions, Literal[True]],
        highlights: Union[HighlightsContentsOptions, Literal[True]],
        summary: Union[SummaryContentsOptions, Literal[True]],
        num_results: Optional[int] = None,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        start_crawl_date: Optional[str] = None,
        end_crawl_date: Optional[str] = None,
        start_published_date: Optional[str] = None,
        end_published_date: Optional[str] = None,
        include_text: Optional[List[str]] = None,
        exclude_text: Optional[List[str]] = None,
        exclude_source_domain: Optional[bool] = None,
        category: Optional[str] = None,
        flags: Optional[List[str]] = None,
        livecrawl_timeout: Optional[int] = None,
        livecrawl: Optional[LIVECRAWL_OPTIONS] = None,
        filter_empty_results: Optional[bool] = None,
        subpages: Optional[int] = None,
        subpage_target: Optional[Union[str, List[str]]] = None,
        extras: Optional[ExtrasOptions] = None,
    ) -> SearchResponse[ResultWithTextAndHighlightsAndSummary]:
        ...

    def find_similar_and_contents(self, url: str, **kwargs):
        options = {k: v for k, v in {"url": url, **kwargs}.items() if v is not None}
        # Default to text if none specified
        if (
            "text" not in options
            and "highlights" not in options
            and "summary" not in options
        ):
            options["text"] = True

        validate_search_options(
            options,
            {
                **FIND_SIMILAR_OPTIONS_TYPES,
                **CONTENTS_OPTIONS_TYPES,
                **CONTENTS_ENDPOINT_OPTIONS_TYPES,
            },
        )
        # We nest the content fields
        options = nest_fields(
            options,
            [
                "text",
                "highlights",
                "summary",
                "subpages",
                "subpage_target",
                "livecrawl",
                "livecrawl_timeout",
                "extras",
            ],
            "contents",
        )
        options = to_camel_case(options)
        data = self.request("/findSimilar", options)
        return SearchResponse(
            [Result(**to_snake_case(result)) for result in data["results"]],
            data.get("autopromptString"),
            data.get("resolvedSearchType"),
            data.get("autoDate"),
        )

    def wrap(self, client: OpenAI):
        """Wrap an OpenAI client with Exa functionality.

        After wrapping, any call to `client.chat.completions.create` will be intercepted 
        and enhanced with Exa RAG functionality. To disable Exa for a specific call, 
        set `use_exa="none"` in the `create` method.

        Args:
            client (OpenAI): The OpenAI client to wrap.

        Returns:
            OpenAI: The wrapped OpenAI client.
        """

        func = client.chat.completions.create

        @wraps(func)
        def create_with_rag(
            # Mandatory OpenAI args
            messages: Iterable[ChatCompletionMessageParam],
            model: Union[str, ChatModel],
            # Exa args
            use_exa: Optional[Literal["required", "none", "auto"]] = "auto",
            highlights: Union[HighlightsContentsOptions, Literal[True], None] = None,
            num_results: Optional[int] = 3,
            include_domains: Optional[List[str]] = None,
            exclude_domains: Optional[List[str]] = None,
            start_crawl_date: Optional[str] = None,
            end_crawl_date: Optional[str] = None,
            start_published_date: Optional[str] = None,
            end_published_date: Optional[str] = None,
            include_text: Optional[List[str]] = None,
            exclude_text: Optional[List[str]] = None,
            use_autoprompt: Optional[bool] = True,
            type: Optional[str] = None,
            category: Optional[str] = None,
            result_max_len: int = 2048,
            flags: Optional[List[str]] = None,
            # OpenAI args
            **openai_kwargs,
        ):
            exa_kwargs = {
                "num_results": num_results,
                "include_domains": include_domains,
                "exclude_domains": exclude_domains,
                "highlights": highlights,
                "start_crawl_date": start_crawl_date,
                "end_crawl_date": end_crawl_date,
                "start_published_date": start_published_date,
                "end_published_date": end_published_date,
                "include_text": include_text,
                "exclude_text": exclude_text,
                "use_autoprompt": use_autoprompt,
                "type": type,
                "category": category,
                "flags": flags,
            }

            create_kwargs = {
                "model": model,
                **openai_kwargs,
            }

            return self._create_with_tool(
                create_fn=func,
                messages=list(messages),
                max_len=result_max_len,
                create_kwargs=create_kwargs,
                exa_kwargs=exa_kwargs,
            )

        print("Wrapping OpenAI client with Exa functionality.")
        client.chat.completions.create = create_with_rag  # type: ignore

        return client

    def _create_with_tool(
        self,
        create_fn: Callable,
        messages: List[ChatCompletionMessageParam],
        max_len,
        create_kwargs,
        exa_kwargs,
    ) -> ExaOpenAICompletion:
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "search",
                    "description": "Search the web for relevant information.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The query to search for.",
                            },
                        },
                        "required": ["query"],
                    },
                },
            }
        ]

        create_kwargs["tools"] = tools

        completion = create_fn(messages=messages, **create_kwargs)

        query = maybe_get_query(completion)

        if not query:
            return ExaOpenAICompletion.from_completion(
                completion=completion, exa_result=None
            )

        # We do a search_and_contents automatically
        exa_result = self.search_and_contents(query, **exa_kwargs)
        exa_str = format_exa_result(exa_result, max_len=max_len)
        new_messages = add_message_to_messages(completion, messages, exa_str)
        completion = create_fn(messages=new_messages, **create_kwargs)

        exa_completion = ExaOpenAICompletion.from_completion(
            completion=completion, exa_result=exa_result
        )
        return exa_completion

    @overload
    def answer(
        self,
        query: str,
        *,
        expanded_queries_limit: Optional[int] = 1,
        stream: Optional[bool] = False,
        include_text: Optional[bool] = False,
    ) -> Union[AnswerResponse, Iterator[Union[str, List[AnswerResult]]]]:
        ...

    def answer(
        self,
        query: str,
        *,
        expanded_queries_limit: Optional[int] = 1,
        stream: Optional[bool] = False,
        include_text: Optional[bool] = False,
    ) -> Union[AnswerResponse, Iterator[Union[str, List[AnswerResult]]]]:
        """Generate an answer to a query using Exa's search and LLM capabilities.

        Args:
            query (str): The query to answer.
            expanded_queries_limit (int, optional): Maximum number of query variations (0-4). Defaults to 1.
            stream (bool, optional): Whether to stream the response. Defaults to False.
            include_text (bool, optional): Whether to include full text in the results. Defaults to False.

        Returns:
            Union[AnswerResponse, Iterator[Union[str, List[AnswerResult]]]]:
                - If stream=False, returns an AnswerResponse object containing the answer and sources.
                - If stream=True, returns an iterator that yields either answer chunks or sources.
        """
        options = {
            k: v
            for k, v in locals().items()
            if k != "self" and v is not None
        }
        options = to_camel_case(options)
        response = self.request("/answer", options)

        if stream:
            return response

        return AnswerResponse(
            response["answer"],
            [AnswerResult(**to_snake_case(result)) for result in response["sources"]]
        )
