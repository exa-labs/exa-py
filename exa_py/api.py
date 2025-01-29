from __future__ import annotations
from dataclasses import dataclass
import dataclasses
from functools import wraps
import re
import os
import httpx  # <-- We now use httpx for both sync and async
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
    Iterator,
    AsyncIterator,
    get_origin,
    get_args,
)
from typing_extensions import TypedDict

from openai import OpenAI
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
from openai.types.chat_model import ChatModel

# We must preserve references to exa_py.utils:
from exa_py.utils import (
    ExaOpenAICompletion,
    add_message_to_messages,
    format_exa_result,
    maybe_get_query,
)

is_beta = os.getenv("IS_BETA") == "True"


# --------------------------------------------------------------------------
# Utility functions, preserved from the original
# --------------------------------------------------------------------------
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


# --------------------------------------------------------------------------
# Type definitions for search, find_similar, contents, etc.
# --------------------------------------------------------------------------
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
    "category": [str],  # A data category to focus on
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


# --------------------------------------------------------------------------
# TypedDict definitions for text/highlights/summary extras
# --------------------------------------------------------------------------
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


# --------------------------------------------------------------------------
# Result classes
# --------------------------------------------------------------------------
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


# --------------------------------------------------------------------------
# Answer classes
# --------------------------------------------------------------------------
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


# --------------------------------------------------------------------------
# Utility function for nesting certain fields under "contents"
# --------------------------------------------------------------------------
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


# --------------------------------------------------------------------------
# The Exa class, now with both sync and async support via httpx
# --------------------------------------------------------------------------
class Exa:
    """A client for interacting with Exa API (both sync and async)."""

    def __init__(
        self,
        api_key: Optional[str],
        base_url: str = "https://api.exa.ai",
        user_agent: str = "exa-py 1.8.4",
    ):
        """
        Initialize the Exa client with the provided API key and optional base URL and user agent.

        Args:
            api_key (str): The API key for authenticating with the Exa API.
            base_url (str, optional): The base URL for the Exa API. Defaults to "https://api.exa.ai".
            user_agent (str, optional): The User-Agent header to send. Defaults to "exa-py 1.8.4".
        """
        if api_key is None:
            env_key = os.environ.get("EXA_API_KEY")
            if env_key is None:
                raise ValueError(
                    "API key must be provided as an argument or in EXA_API_KEY environment variable"
                )
            else:
                api_key = env_key

        self.base_url = base_url
        self.api_key = api_key
        self.user_agent = user_agent

        # Prepare sync + async clients
        self._sync_client = httpx.Client(
            base_url=self.base_url,
            headers={
                "x-api-key": self.api_key,
                "User-Agent": self.user_agent,
            },
        )
        self._async_client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "x-api-key": self.api_key,
                "User-Agent": self.user_agent,
            },
        )

    # ----------------------------------------------------------------------
    # Internal request methods (sync + async)
    # ----------------------------------------------------------------------
    def _request_sync(self, endpoint: str, data: dict):
        """Send a POST request to the Exa API (sync). If data['stream'] is True, yields a generator of lines."""
        if data.get("stream"):
            # streaming
            with self._sync_client.stream("POST", endpoint, json=data) as response:
                if response.status_code != 200:
                    raise ValueError(
                        f"Request failed with status code {response.status_code}: {response.text}"
                    )

                def line_iterator() -> Iterator[str]:
                    buffer = ""
                    for chunk in response.iter_text():
                        buffer += chunk
                        while "\n" in buffer:
                            line, buffer = buffer.split("\n", 1)
                            yield line

                return line_iterator()
        else:
            response = self._sync_client.post(endpoint, json=data)
            if response.status_code != 200:
                raise ValueError(
                    f"Request failed with status code {response.status_code}: {response.text}"
                )
            return response.json()

    async def _request_async(self, endpoint: str, data: dict):
        """Send a POST request to the Exa API (async). If data['stream'] is True, yields an async generator of lines."""
        if data.get("stream"):
            # streaming
            response = await self._async_client.stream("POST", endpoint, json=data)
            if response.status_code != 200:
                txt = await response.aread()
                raise ValueError(
                    f"Request failed with status code {response.status_code}: {txt.decode('utf-8','ignore')}"
                )

            async def aline_iterator() -> AsyncIterator[str]:
                buffer = ""
                async for chunk in response.aiter_text():
                    buffer += chunk
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        yield line

            return aline_iterator()
        else:
            response = await self._async_client.post(endpoint, json=data)
            if response.status_code != 200:
                txt = await response.aread()
                raise ValueError(
                    f"Request failed with status code {response.status_code}: {txt.decode('utf-8','ignore')}"
                )
            return response.json()

    # ----------------------------------------------------------------------
    # Sync convenience method for backward compatibility
    # ----------------------------------------------------------------------
    def request(self, endpoint: str, data):
        """
        Legacy sync request convenience method. 
        This calls _request_sync under the hood.
        """
        return self._request_sync(endpoint, data)

    # ----------------------------------------------------------------------
    # Async convenience method
    # ----------------------------------------------------------------------
    async def request_async(self, endpoint: str, data):
        """
        Async request convenience method, calls _request_async under the hood.
        """
        return await self._request_async(endpoint, data)

    # ----------------------------------------------------------------------
    # DRY internal logic for search, get_contents, find_similar, answer
    # We define private methods that do validation, transform data, parse results.
    # The is_async flag determines whether to run sync or async request.
    # ----------------------------------------------------------------------
    def _search_internal(
        self,
        options: Dict[str, object],
        is_async: bool = False,
    ) -> Union[SearchResponse[_Result], AsyncIterator[SearchResponse[_Result]]]:
        """
        DRY method for performing a search. 
        If is_async is True, we do async via _request_async.
        Otherwise, we do sync via _request_sync.
        """
        validate_search_options(options, SEARCH_OPTIONS_TYPES)
        options = to_camel_case(options)
        endpoint = "/search"

        if not is_async:
            data = self._request_sync(endpoint, options)
            # parse results
            results = [Result(**to_snake_case(r)) for r in data["results"]]
            return SearchResponse(
                results=results,
                autoprompt_string=data.get("autopromptString"),
                resolved_search_type=data.get("resolvedSearchType"),
                auto_date=data.get("autoDate"),
            )
        else:
            # Return an awaitable
            async def _runner():
                resp = await self._request_async(endpoint, options)
                results = [Result(**to_snake_case(r)) for r in resp["results"]]
                return SearchResponse(
                    results=results,
                    autoprompt_string=resp.get("autopromptString"),
                    resolved_search_type=resp.get("resolvedSearchType"),
                    auto_date=resp.get("autoDate"),
                )

            return _runner()

    def _search_and_contents_internal(
        self,
        options: Dict[str, object],
        is_async: bool = False,
    ) -> Union[SearchResponse[Result], AsyncIterator[SearchResponse[Result]]]:
        """
        DRY method for performing search+contents.
        """
        combined_validation = {
            **SEARCH_OPTIONS_TYPES,
            **CONTENTS_OPTIONS_TYPES,
            **CONTENTS_ENDPOINT_OPTIONS_TYPES,
        }
        validate_search_options(options, combined_validation)

        # If user didn't ask for any content, default to text
        if (
            "text" not in options
            and "highlights" not in options
            and "summary" not in options
            and "extras" not in options
        ):
            options["text"] = True

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
        endpoint = "/search"

        if not is_async:
            data = self._request_sync(endpoint, options)
            results = [Result(**to_snake_case(r)) for r in data["results"]]
            return SearchResponse(
                results=results,
                autoprompt_string=data.get("autopromptString"),
                resolved_search_type=data.get("resolvedSearchType"),
                auto_date=data.get("autoDate"),
            )
        else:
            async def _runner():
                resp = await self._request_async(endpoint, options)
                results = [Result(**to_snake_case(r)) for r in resp["results"]]
                return SearchResponse(
                    results=results,
                    autoprompt_string=resp.get("autopromptString"),
                    resolved_search_type=resp.get("resolvedSearchType"),
                    auto_date=resp.get("autoDate"),
                )

            return _runner()

    def _get_contents_internal(
        self,
        options: Dict[str, object],
        is_async: bool = False,
    ) -> Union[SearchResponse[Result], AsyncIterator[SearchResponse[Result]]]:
        """
        DRY method for get_contents.
        """
        combined_validation = {
            **CONTENTS_OPTIONS_TYPES,
            **CONTENTS_ENDPOINT_OPTIONS_TYPES,
        }
        validate_search_options(options, combined_validation)

        if (
            "text" not in options
            and "highlights" not in options
            and "summary" not in options
            and "extras" not in options
        ):
            options["text"] = True

        options = to_camel_case(options)
        endpoint = "/contents"

        if not is_async:
            data = self._request_sync(endpoint, options)
            results = [Result(**to_snake_case(r)) for r in data["results"]]
            return SearchResponse(
                results=results,
                autoprompt_string=data.get("autopromptString"),
                resolved_search_type=data.get("resolvedSearchType"),
                auto_date=data.get("autoDate"),
            )
        else:
            async def _runner():
                resp = await self._request_async(endpoint, options)
                results = [Result(**to_snake_case(r)) for r in resp["results"]]
                return SearchResponse(
                    results=results,
                    autoprompt_string=resp.get("autopromptString"),
                    resolved_search_type=resp.get("resolvedSearchType"),
                    auto_date=resp.get("autoDate"),
                )

            return _runner()

    def _find_similar_internal(
        self,
        options: Dict[str, object],
        is_async: bool = False,
        contents: bool = False,
    ) -> Union[SearchResponse[Result], AsyncIterator[SearchResponse[Result]]]:
        """
        DRY method for find_similar and find_similar_and_contents.
        """
        if contents:
            # validate with both
            combined_validation = {
                **FIND_SIMILAR_OPTIONS_TYPES,
                **CONTENTS_OPTIONS_TYPES,
                **CONTENTS_ENDPOINT_OPTIONS_TYPES,
            }
            validate_search_options(options, combined_validation)

            if (
                "text" not in options
                and "highlights" not in options
                and "summary" not in options
                and "extras" not in options
            ):
                options["text"] = True

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
        else:
            validate_search_options(options, FIND_SIMILAR_OPTIONS_TYPES)

        options = to_camel_case(options)
        endpoint = "/findSimilar"

        if not is_async:
            data = self._request_sync(endpoint, options)
            results = [Result(**to_snake_case(r)) for r in data["results"]]
            return SearchResponse(
                results=results,
                autoprompt_string=data.get("autopromptString"),
                resolved_search_type=data.get("resolvedSearchType"),
                auto_date=data.get("autoDate"),
            )
        else:
            async def _runner():
                resp = await self._request_async(endpoint, options)
                results = [Result(**to_snake_case(r)) for r in resp["results"]]
                return SearchResponse(
                    results=results,
                    autoprompt_string=resp.get("autopromptString"),
                    resolved_search_type=resp.get("resolvedSearchType"),
                    auto_date=resp.get("autoDate"),
                )

            return _runner()

    def _answer_internal(
        self,
        options: Dict[str, object],
        is_async: bool = False,
    ) -> Union[
        AnswerResponse, Iterator[Union[str, List[AnswerResult]]], AsyncIterator[Union[str, List[AnswerResult]]]
    ]:
        """
        DRY method for /answer. Potentially streaming.
        """
        options = to_camel_case(options)
        endpoint = "/answer"

        if not is_async:
            resp = self._request_sync(endpoint, options)
            # If streaming, resp might be an iterator
            if hasattr(resp, "__iter__") and not isinstance(resp, dict):
                # It's a streaming generator of lines
                def _sync_stream():
                    for chunk in resp:
                        yield chunk

                return _sync_stream()
            else:
                # normal JSON
                return AnswerResponse(
                    answer=resp["answer"],
                    sources=[AnswerResult(**to_snake_case(s)) for s in resp["sources"]],
                )
        else:
            async def _runner():
                r = await self._request_async(endpoint, options)
                # If streaming
                # We check if it's a coroutine generator
                if hasattr(r, "__aiter__") and callable(r.__aiter__):
                    # It's an async generator
                    async def _async_stream():
                        async for chunk in r:
                            yield chunk

                    return _async_stream()
                else:
                    # normal JSON
                    return AnswerResponse(
                        answer=r["answer"],
                        sources=[AnswerResult(**to_snake_case(s)) for s in r["sources"]],
                    )

            return _runner()

    # --------------------------------------------------------------------------
    # Public Sync Methods
    # --------------------------------------------------------------------------
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
        """
        Perform a search with a prompt-engineered query to retrieve relevant results (sync).
        """
        opts = {k: v for k, v in locals().items() if k != "self" and v is not None}
        return self._search_internal(opts, is_async=False)

    def search_and_contents(self, query: str, **kwargs):
        """
        Perform a search with a query to retrieve relevant results,
        and also retrieve specified content fields (text, highlights, summary, etc). (sync)
        """
        opts = {"query": query}
        for k, v in kwargs.items():
            if v is not None:
                opts[k] = v
        return self._search_and_contents_internal(opts, is_async=False)

    def get_contents(self, urls: Union[str, List[str], List[_Result]], **kwargs):
        """
        Given a list of URLs (or single URL or list of _Result), retrieve content
        such as text, highlights, summary, etc. (sync)
        """
        if isinstance(urls, list) and urls and isinstance(urls[0], _Result):
            urls = [r.url for r in urls]
        elif isinstance(urls, _Result):
            urls = [urls.url]

        opts = {"urls": urls}
        for k, v in kwargs.items():
            if v is not None:
                opts[k] = v

        return self._get_contents_internal(opts, is_async=False)

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
        """
        Finds similar pages to a given URL, potentially with domain filters and date filters. (sync)
        """
        opts = {k: v for k, v in locals().items() if k != "self" and v is not None}
        return self._find_similar_internal(opts, is_async=False, contents=False)

    def find_similar_and_contents(self, url: str, **kwargs):
        """
        Finds similar pages to a given URL and also retrieves requested content fields (text, highlights, summary, etc). (sync)
        """
        opts = {"url": url}
        for k, v in kwargs.items():
            if v is not None:
                opts[k] = v
        return self._find_similar_internal(opts, is_async=False, contents=True)

    def answer(
        self,
        query: str,
        *,
        expanded_queries_limit: Optional[int] = 1,
        stream: Optional[bool] = False,
        include_text: Optional[bool] = False,
    ) -> Union[AnswerResponse, Iterator[Union[str, List[AnswerResult]]]]:
        """
        Generate an answer to a query using Exa's search and LLM capabilities. (sync)
        Possible streaming if stream=True.
        """
        opts = {k: v for k, v in locals().items() if k != "self" and v is not None}
        return self._answer_internal(opts, is_async=False)

    # --------------------------------------------------------------------------
    # Public Async Methods (using _async suffix)
    # --------------------------------------------------------------------------
    async def search_async(
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
        """
        Perform a search with a prompt-engineered query to retrieve relevant results (async).
        """
        opts = {k: v for k, v in locals().items() if k != "self" and v is not None}
        runner = self._search_internal(opts, is_async=True)
        return await runner  # runner is an async function

    async def search_and_contents_async(self, query: str, **kwargs):
        """
        Perform a search with a query to retrieve relevant results,
        and also retrieve specified content fields (text, highlights, summary, etc). (async)
        """
        opts = {"query": query}
        for k, v in kwargs.items():
            if v is not None:
                opts[k] = v
        runner = self._search_and_contents_internal(opts, is_async=True)
        return await runner

    async def get_contents_async(self, urls: Union[str, List[str], List[_Result]], **kwargs):
        """
        Given a list of URLs (or single URL or list of _Result), retrieve content
        such as text, highlights, summary, etc. (async)
        """
        if isinstance(urls, list) and urls and isinstance(urls[0], _Result):
            urls = [r.url for r in urls]
        elif isinstance(urls, _Result):
            urls = [urls.url]

        opts = {"urls": urls}
        for k, v in kwargs.items():
            if v is not None:
                opts[k] = v

        runner = self._get_contents_internal(opts, is_async=True)
        return await runner

    async def find_similar_async(
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
        """
        Finds similar pages to a given URL, potentially with domain filters and date filters. (async)
        """
        opts = {k: v for k, v in locals().items() if k != "self" and v is not None}
        runner = self._find_similar_internal(opts, is_async=True, contents=False)
        return await runner

    async def find_similar_and_contents_async(self, url: str, **kwargs):
        """
        Finds similar pages to a given URL and also retrieves requested content fields (text, highlights, summary, etc). (async)
        """
        opts = {"url": url}
        for k, v in kwargs.items():
            if v is not None:
                opts[k] = v
        runner = self._find_similar_internal(opts, is_async=True, contents=True)
        return await runner

    async def answer_async(
        self,
        query: str,
        *,
        expanded_queries_limit: Optional[int] = 1,
        stream: Optional[bool] = False,
        include_text: Optional[bool] = False,
    ) -> Union[AnswerResponse, AsyncIterator[Union[str, List[AnswerResult]]]]:
        """
        Generate an answer to a query using Exa's search and LLM capabilities. (async)
        If stream=True, returns an async iterator that yields partial answer strings or the final sources.
        """
        opts = {k: v for k, v in locals().items() if k != "self" and v is not None}
        runner = self._answer_internal(opts, is_async=True)
        result = await runner

        # If streaming, result is an async generator
        if callable(getattr(result, "__aiter__", None)):
            # It's an async generator
            return result
        else:
            # It's an AnswerResponse
            return result

    # --------------------------------------------------------------------------
    # wrap method for integration with OpenAI, preserving the original doc
    # --------------------------------------------------------------------------
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
        max_len: int,
        create_kwargs: dict,
        exa_kwargs: dict,
    ) -> ExaOpenAICompletion:
        """
        Internal method used by `wrap`. It intercepts an OpenAI completion call,
        checks for a user query, does search_and_contents, then re-calls create_fn
        with the top results appended to the conversation, returning an ExaOpenAICompletion.
        """
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

        # Insert "tools" param for function calling
        create_kwargs["tools"] = tools

        # First get the initial completion
        completion = create_fn(messages=messages, **create_kwargs)

        # Maybe parse a search query from that
        query = maybe_get_query(completion)
        if not query:
            # No query found, just wrap completion
            return ExaOpenAICompletion.from_completion(
                completion=completion, exa_result=None
            )

        # If we do have a query, run Exa search
        exa_result = self.search_and_contents(query, **exa_kwargs)

        # Format results as text to feed back
        exa_str = format_exa_result(exa_result, max_len=max_len)
        new_messages = add_message_to_messages(completion, messages, exa_str)

        # Re-invoke create_fn with the new messages
        completion = create_fn(messages=new_messages, **create_kwargs)

        # Return a specialized object that wraps the final completion
        return ExaOpenAICompletion.from_completion(
            completion=completion,
            exa_result=exa_result
        )
