from __future__ import annotations

import dataclasses
import json
import os
import re
from dataclasses import dataclass
from functools import wraps
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    Iterable,
    Iterator,
    List,
    Literal,
    Optional,
    TypeVar,
    Union,
    get_args,
    get_origin,
    overload,
)

from .websets import AsyncWebsetsClient
import httpx
import requests
from openai import OpenAI
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
from openai.types.chat_model import ChatModel
from typing_extensions import TypedDict

from exa_py.utils import (
    ExaOpenAICompletion,
    _convert_schema_input,
    _get_package_version,
    add_message_to_messages,
    format_exa_result,
    maybe_get_query,
    JSONSchemaInput,
)
from .websets import WebsetsClient
from .websets.core.base import ExaJSONEncoder
from .research import ResearchClient, AsyncResearchClient


is_beta = os.getenv("IS_BETA") == "True"


def snake_to_camel(snake_str: str) -> str:
    """Convert snake_case string to camelCase.

    Args:
        snake_str (str): The string in snake_case format.

    Returns:
        str: The string converted to camelCase format.
    """
    # Handle special cases where the field should start with non-alphanumeric characters
    if snake_str == "schema_":
        return "$schema"
    if snake_str == "not_":
        return "not"

    components = snake_str.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


def to_camel_case(data: dict, skip_keys: list[str] = []) -> dict:
    """
    Convert keys in a dictionary from snake_case to camelCase recursively.

    Args:
        data (dict): The dictionary with keys in snake_case format.

    Returns:
        dict: The dictionary with keys converted to camelCase format.
    """
    if isinstance(data, dict):
        return {
            snake_to_camel(k): to_camel_case(v, skip_keys)
            if isinstance(v, dict) and k not in skip_keys
            else v
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
    "include_domains": [
        list
    ],  # Domains to search from; exclusive with 'exclude_domains'.
    "exclude_domains": [list],  # Domains to omit; exclusive with 'include_domains'.
    "start_crawl_date": [str],  # Results after this crawl date. ISO 8601 format.
    "end_crawl_date": [str],  # Results before this crawl date. ISO 8601 format.
    "start_published_date": [
        str
    ],  # Results after this publish date; excludes links with no date. ISO 8601 format.
    "end_published_date": [
        str
    ],  # Results before this publish date; excludes links with no date. ISO 8601 format.
    "user_location": [str],  # Two-letter ISO country code of the user (e.g. US).
    "include_text": [
        list
    ],  # Must be present in webpage text. (One string, up to 5 words)
    "exclude_text": [
        list
    ],  # Must not be present in webpage text. (One string, up to 5 words)
    "use_autoprompt": [bool],  # Convert query to Exa. (Default: false)
    "type": [str],  # 'keyword', 'neural', 'hybrid', 'fast', or 'auto' (Default: auto)
    "category": [
        str
    ],  # A data category to focus on: 'company', 'research paper', 'news', 'pdf', 'github', 'tweet', 'personal site', 'linkedin profile', 'financial report'
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
LIVECRAWL_OPTIONS = Literal["always", "fallback", "never", "auto", "preferred"]

CONTENTS_OPTIONS_TYPES = {
    "urls": [list],
    "text": [dict, bool],
    "highlights": [dict, bool],
    "summary": [dict, bool],
    "context": [dict, bool],
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


def parse_cost_dollars(raw: dict) -> Optional[CostDollars]:
    """
    Parse the costDollars JSON into a CostDollars object, or return None if missing/invalid.
    """
    if not raw:
        return None

    total = raw.get("total")
    if total is None:
        # If there's no total, treat as absent
        return None

    # search and contents can be dictionaries or None
    search_part = raw.get("search")
    contents_part = raw.get("contents")

    return CostDollars(total=total, search=search_part, contents=contents_part)


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


class JSONSchema(TypedDict, total=False):
    """Represents a JSON Schema definition used for structured summary output.

    .. deprecated:: 1.15.0
        Use Pydantic models or dict[str, Any] directly instead.
        This will be removed in a future version.

    To learn more visit https://json-schema.org/overview/what-is-jsonschema.
    """

    schema_: str  # This will be converted to "$schema" in JSON
    title: str
    description: str
    type: Literal["object", "array", "string", "number", "boolean", "null", "integer"]
    properties: Dict[str, JSONSchema]
    items: Union[JSONSchema, List[JSONSchema]]
    required: List[str]
    enum: List
    additionalProperties: Union[bool, JSONSchema]
    definitions: Dict[str, JSONSchema]
    patternProperties: Dict[str, JSONSchema]
    allOf: List[JSONSchema]
    anyOf: List[JSONSchema]
    oneOf: List[JSONSchema]
    not_: JSONSchema  # This will be converted to "not" in JSON


class SummaryContentsOptions(TypedDict, total=False):
    """A class representing the options that you can specify when requesting summary

    Attributes:
        query (str): The query string for the summary. Summary will bias towards answering the query.
        schema (Union[BaseModel, dict[str, Any]]): JSON schema for structured output from summary.
            Can be a Pydantic model (automatically converted) or a dict containing JSON Schema.
    """

    query: str
    schema: JSONSchemaInput


class ContextContentsOptions(TypedDict, total=False):
    """Options for retrieving aggregated context from a set of search results.

    Attributes:
        max_characters (int): The maximum number of characters to include in the context string.
    """

    max_characters: int


class ExtrasOptions(TypedDict, total=False):
    """A class representing additional extraction fields (e.g. links, images)"""

    links: int
    image_links: int


class CostDollarsSearch(TypedDict, total=False):
    """Represents the cost breakdown for search."""

    neural: float
    keyword: float


class CostDollarsContents(TypedDict, total=False):
    """Represents the cost breakdown for contents."""

    text: float
    highlights: float
    summary: float


@dataclass
class CostDollars:
    """Represents costDollars field in the API response."""

    total: float
    search: CostDollarsSearch = None
    contents: CostDollarsContents = None


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

    def __init__(
        self,
        url,
        id,
        title=None,
        score=None,
        published_date=None,
        author=None,
        image=None,
        favicon=None,
        subpages=None,
        extras=None,
    ):
        self.url = url
        self.id = id
        self.title = title
        self.score = score
        self.published_date = published_date
        self.author = author
        self.image = image
        self.favicon = favicon
        self.subpages = subpages
        self.extras = extras

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

    def __init__(
        self,
        url,
        id,
        title=None,
        score=None,
        published_date=None,
        author=None,
        image=None,
        favicon=None,
        subpages=None,
        extras=None,
        text=None,
        highlights=None,
        highlight_scores=None,
        summary=None,
    ):
        super().__init__(
            url,
            id,
            title,
            score,
            published_date,
            author,
            image,
            favicon,
            subpages,
            extras,
        )
        self.text = text
        self.highlights = highlights
        self.highlight_scores = highlight_scores
        self.summary = summary

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

    def __init__(
        self,
        url,
        id,
        title=None,
        score=None,
        published_date=None,
        author=None,
        image=None,
        favicon=None,
        subpages=None,
        extras=None,
        text="",
    ):
        super().__init__(
            url,
            id,
            title,
            score,
            published_date,
            author,
            image,
            favicon,
            subpages,
            extras,
        )
        self.text = text

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

    def __init__(
        self,
        url,
        id,
        title=None,
        score=None,
        published_date=None,
        author=None,
        image=None,
        favicon=None,
        subpages=None,
        extras=None,
        highlights=None,
        highlight_scores=None,
    ):
        super().__init__(
            url,
            id,
            title,
            score,
            published_date,
            author,
            image,
            favicon,
            subpages,
            extras,
        )
        self.highlights = highlights if highlights is not None else []
        self.highlight_scores = highlight_scores if highlight_scores is not None else []

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

    def __init__(
        self,
        url,
        id,
        title=None,
        score=None,
        published_date=None,
        author=None,
        image=None,
        favicon=None,
        subpages=None,
        extras=None,
        text="",
        highlights=None,
        highlight_scores=None,
    ):
        super().__init__(
            url,
            id,
            title,
            score,
            published_date,
            author,
            image,
            favicon,
            subpages,
            extras,
        )
        self.text = text
        self.highlights = highlights if highlights is not None else []
        self.highlight_scores = highlight_scores if highlight_scores is not None else []

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

    def __init__(
        self,
        url,
        id,
        title=None,
        score=None,
        published_date=None,
        author=None,
        image=None,
        favicon=None,
        subpages=None,
        extras=None,
        summary="",
    ):
        super().__init__(
            url,
            id,
            title,
            score,
            published_date,
            author,
            image,
            favicon,
            subpages,
            extras,
        )
        self.summary = summary

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

    def __init__(
        self,
        url,
        id,
        title=None,
        score=None,
        published_date=None,
        author=None,
        image=None,
        favicon=None,
        subpages=None,
        extras=None,
        text="",
        summary="",
    ):
        super().__init__(
            url,
            id,
            title,
            score,
            published_date,
            author,
            image,
            favicon,
            subpages,
            extras,
        )
        self.text = text
        self.summary = summary

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

    def __init__(
        self,
        url,
        id,
        title=None,
        score=None,
        published_date=None,
        author=None,
        image=None,
        favicon=None,
        subpages=None,
        extras=None,
        highlights=None,
        highlight_scores=None,
        summary="",
    ):
        super().__init__(
            url,
            id,
            title,
            score,
            published_date,
            author,
            image,
            favicon,
            subpages,
            extras,
        )
        self.highlights = highlights if highlights is not None else []
        self.highlight_scores = highlight_scores if highlight_scores is not None else []
        self.summary = summary

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

    def __init__(
        self,
        url,
        id,
        title=None,
        score=None,
        published_date=None,
        author=None,
        image=None,
        favicon=None,
        subpages=None,
        extras=None,
        text="",
        highlights=None,
        highlight_scores=None,
        summary="",
    ):
        super().__init__(
            url,
            id,
            title,
            score,
            published_date,
            author,
            image,
            favicon,
            subpages,
            extras,
        )
        self.text = text
        self.highlights = highlights if highlights is not None else []
        self.highlight_scores = highlight_scores if highlight_scores is not None else []
        self.summary = summary

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
    """A class representing a result for an answer.

    Attributes:
        title (str): The title of the search result.
        url (str): The URL of the search result.
        id (str): The temporary ID for the document.
        published_date (str, optional): An estimate of the creation date, from parsing HTML content.
        author (str, optional): If available, the author of the content.
        text (str, optional): The full page text from each search result.
    """

    id: str
    url: str
    title: Optional[str] = None
    published_date: Optional[str] = None
    author: Optional[str] = None
    text: Optional[str] = None

    def __init__(
        self, id, url, title=None, published_date=None, author=None, text=None
    ):
        self.id = id
        self.url = url
        self.title = title
        self.published_date = published_date
        self.author = author
        self.text = text

    def __str__(self):
        return (
            f"Title: {self.title}\n"
            f"URL: {self.url}\n"
            f"ID: {self.id}\n"
            f"Published Date: {self.published_date}\n"
            f"Author: {self.author}\n"
            f"Text: {self.text}\n\n"
        )


@dataclass
class StreamChunk:
    """A class representing a single chunk of streaming data.

    Attributes:
        content (Optional[str]): The partial text content of the answer
        citations (Optional[List[AnswerResult]]): List of citations if provided in this chunk
    """

    content: Optional[str] = None
    citations: Optional[List[AnswerResult]] = None

    def has_data(self) -> bool:
        """Check if this chunk contains any data."""
        return self.content is not None or self.citations is not None

    def __str__(self) -> str:
        """Format the chunk data as a string."""
        output = ""
        if self.content:
            output += self.content
        if self.citations:
            output += "\nCitations:"
            for source in self.citations:
                output += f"\n{source}"
        return output


@dataclass
class AnswerResponse:
    """A class representing the response for an answer operation.

    Attributes:
        answer (str): The generated answer.
        citations (List[AnswerResult]): A list of citations used to generate the answer.
    """

    answer: Union[str, dict[str, Any]]
    citations: List[AnswerResult]

    def __str__(self):
        output = f"Answer: {self.answer}\n\nCitations:"
        for source in self.citations:
            output += f"\nTitle: {source.title}"
            output += f"\nID: {source.id}"
            output += f"\nURL: {source.url}"
            output += f"\nPublished Date: {source.published_date}"
            output += f"\nAuthor: {source.author}"
            output += f"\nText: {source.text}"
            output += "\n"
        return output


class StreamAnswerResponse:
    """A class representing a streaming answer response."""

    def __init__(self, raw_response: requests.Response):
        self._raw_response = raw_response
        self._ensure_ok_status()

    def _ensure_ok_status(self):
        if self._raw_response.status_code != 200:
            raise ValueError(
                f"Request failed with status code {self._raw_response.status_code}: {self._raw_response.text}"
            )

    def __iter__(self) -> Iterator[StreamChunk]:
        for line in self._raw_response.iter_lines():
            if not line:
                continue
            decoded_line = line.decode("utf-8").removeprefix("data: ")
            try:
                chunk = json.loads(decoded_line)
            except json.JSONDecodeError:
                continue

            content = None
            citations = None

            if "choices" in chunk and chunk["choices"]:
                if "delta" in chunk["choices"][0]:
                    content = chunk["choices"][0]["delta"].get("content")

            if (
                "citations" in chunk
                and chunk["citations"]
                and chunk["citations"] != "null"
            ):
                citations = []
                for s in chunk["citations"]:
                    snake_s = to_snake_case(s)
                    citations.append(
                        AnswerResult(
                            id=snake_s.get("id"),
                            url=snake_s.get("url"),
                            title=snake_s.get("title"),
                            published_date=snake_s.get("published_date"),
                            author=snake_s.get("author"),
                            text=snake_s.get("text"),
                        )
                    )

            stream_chunk = StreamChunk(content=content, citations=citations)
            if stream_chunk.has_data():
                yield stream_chunk

    def close(self) -> None:
        """Close the underlying raw response to release the network socket."""
        self._raw_response.close()


class AsyncStreamAnswerResponse:
    """A class representing a streaming answer response."""

    def __init__(self, raw_response: httpx.Response):
        self._raw_response = raw_response
        self._ensure_ok_status()

    def _ensure_ok_status(self):
        if self._raw_response.status_code != 200:
            raise ValueError(
                f"Request failed with status code {self._raw_response.status_code}: {self._raw_response.text}"
            )

    def __aiter__(self):
        async def generator():
            async for line in self._raw_response.aiter_lines():
                if not line:
                    continue
                decoded_line = line.removeprefix("data: ")
                try:
                    chunk = json.loads(decoded_line)
                except json.JSONDecodeError:
                    continue

                content = None
                citations = None

                if "choices" in chunk and chunk["choices"]:
                    if "delta" in chunk["choices"][0]:
                        content = chunk["choices"][0]["delta"].get("content")

                if (
                    "citations" in chunk
                    and chunk["citations"]
                    and chunk["citations"] != "null"
                ):
                    citations = []
                    for s in chunk["citations"]:
                        snake_s = to_snake_case(s)
                        citations.append(
                            AnswerResult(
                                id=snake_s.get("id"),
                                url=snake_s.get("url"),
                                title=snake_s.get("title"),
                                published_date=snake_s.get("published_date"),
                                author=snake_s.get("author"),
                                text=snake_s.get("text"),
                            )
                        )

                stream_chunk = StreamChunk(content=content, citations=citations)
                if stream_chunk.has_data():
                    yield stream_chunk

        return generator()

    def close(self) -> None:
        """Close the underlying raw response to release the network socket."""
        self._raw_response.close()


T = TypeVar("T")


@dataclass
class ContentStatus:
    """A class representing the status of a content retrieval operation."""

    id: str
    status: str
    source: str


@dataclass
class SearchResponse(Generic[T]):
    """A class representing the response for a search operation.

    Attributes:
        results (List[Result]): A list of search results.
        autoprompt_string (str, optional): The Exa query created by autoprompt.
        resolved_search_type (str, optional): 'neural' or 'keyword' if auto.
        auto_date (str, optional): A date for filtering if autoprompt found one.
        context (str, optional): Combined context string when requested via contents.context.
        statuses (List[ContentStatus], optional): Status list from get_contents.
        cost_dollars (CostDollars, optional): Cost breakdown.
    """

    results: List[T]
    autoprompt_string: Optional[str]
    resolved_search_type: Optional[str]
    auto_date: Optional[str]
    context: Optional[str] = None
    statuses: Optional[List[ContentStatus]] = None
    cost_dollars: Optional[CostDollars] = None

    def __str__(self):
        output = "\n\n".join(str(result) for result in self.results)
        if self.context:
            output += f"\nContext: {self.context}"
        if self.autoprompt_string:
            output += f"\n\nAutoprompt String: {self.autoprompt_string}"
        if self.resolved_search_type:
            output += f"\nResolved Search Type: {self.resolved_search_type}"
        if self.cost_dollars:
            output += f"\nCostDollars: total={self.cost_dollars.total}"
            if self.cost_dollars.search:
                output += f"\n  - search: {self.cost_dollars.search}"
            if self.cost_dollars.contents:
                output += f"\n  - contents: {self.cost_dollars.contents}"
        if self.statuses:
            output += f"\nStatuses: {self.statuses}"
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
        user_agent: Optional[str] = None,
    ):
        """Initialize the Exa client with the provided API key and optional base URL and user agent.

        Args:
            api_key (str): The API key for authenticating with the Exa API.
            base_url (str, optional): The base URL for the Exa API. Defaults to "https://api.exa.ai".
            user_agent (str, optional): Custom user agent. Defaults to "exa-py {version}".
        """
        if api_key is None:
            import os

            api_key = os.environ.get("EXA_API_KEY")
            if api_key is None:
                raise ValueError(
                    "API key must be provided as an argument or in EXA_API_KEY environment variable"
                )

        # Set default user agent with dynamic version if not provided
        if user_agent is None:
            user_agent = f"exa-py {_get_package_version()}"

        self.base_url = base_url
        self.headers = {
            "x-api-key": api_key,
            "User-Agent": user_agent,
            "Content-Type": "application/json",
        }
        self.websets = WebsetsClient(self)
        # Research tasks client (new, mirrors Websets design)
        self.research = ResearchClient(self)

    def request(
        self,
        endpoint: str,
        data: Optional[Union[Dict[str, Any], str]] = None,
        method: str = "POST",
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Union[Dict[str, Any], requests.Response]:
        """Send a request to the Exa API, optionally streaming if data['stream'] is True.

        Args:
            endpoint (str): The API endpoint (path).
            data (dict, optional): The JSON payload to send. Defaults to None.
            method (str, optional): The HTTP method to use. Defaults to "POST".
            params (Dict[str, Any], optional): Query parameters to include. Defaults to None.
            headers (Dict[str, str], optional): Additional headers to include in the request. Defaults to None.

        Returns:
            Union[dict, requests.Response]: If streaming, returns the Response object.
            Otherwise, returns the JSON-decoded response as a dict.

        Raises:
            ValueError: If the request fails (non-200 status code).
        """
        # Handle the case when data is a string
        if isinstance(data, str):
            # Use the string directly as the data payload
            json_data = data
        else:
            # Otherwise, serialize the dictionary to JSON if it exists
            json_data = json.dumps(data, cls=ExaJSONEncoder) if data else None

        # Check if we need streaming (either from data for POST or params for GET)
        needs_streaming = (data and isinstance(data, dict) and data.get("stream")) or (
            params and params.get("stream") == "true"
        )

        # Merge additional headers with existing headers
        request_headers = {**self.headers}
        if headers:
            request_headers.update(headers)

        if method.upper() == "GET":
            if needs_streaming:
                res = requests.get(
                    self.base_url + endpoint,
                    headers=request_headers,
                    params=params,
                    stream=True,
                )
                return res
            else:
                res = requests.get(
                    self.base_url + endpoint, headers=request_headers, params=params
                )
        elif method.upper() == "POST":
            if needs_streaming:
                res = requests.post(
                    self.base_url + endpoint,
                    data=json_data,
                    headers=request_headers,
                    stream=True,
                )
                return res
            else:
                res = requests.post(
                    self.base_url + endpoint, data=json_data, headers=request_headers
                )
        elif method.upper() == "PATCH":
            res = requests.patch(
                self.base_url + endpoint, data=json_data, headers=request_headers
            )
        elif method.upper() == "DELETE":
            res = requests.delete(self.base_url + endpoint, headers=request_headers)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        if res.status_code >= 400:
            raise ValueError(
                f"Request failed with status code {res.status_code}: {res.text}"
            )
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
        user_location: Optional[str] = None,
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
            type (str, optional): 'keyword', 'neural', 'hybrid', 'fast', or 'auto' (default 'auto').
            category (str, optional): e.g. 'company'
            flags (List[str], optional): Experimental flags for Exa usage.
            moderation (bool, optional): If True, the search results will be moderated for safety.
            user_location (str, optional): Two-letter ISO country code of the user (e.g. US).

        Returns:
            SearchResponse: The response containing search results, etc.
        """
        options = {k: v for k, v in locals().items() if k != "self" and v is not None}
        validate_search_options(options, SEARCH_OPTIONS_TYPES)
        options = to_camel_case(options)
        data = self.request("/search", options)
        cost_dollars = parse_cost_dollars(data.get("costDollars"))
        results = []
        for result in data["results"]:
            snake_result = to_snake_case(result)
            results.append(
                Result(
                    url=snake_result.get("url"),
                    id=snake_result.get("id"),
                    title=snake_result.get("title"),
                    score=snake_result.get("score"),
                    published_date=snake_result.get("published_date"),
                    author=snake_result.get("author"),
                    image=snake_result.get("image"),
                    favicon=snake_result.get("favicon"),
                    subpages=snake_result.get("subpages"),
                    extras=snake_result.get("extras"),
                    text=snake_result.get("text"),
                    highlights=snake_result.get("highlights"),
                    highlight_scores=snake_result.get("highlight_scores"),
                    summary=snake_result.get("summary"),
                )
            )
        return SearchResponse(
            results,
            data["autopromptString"] if "autopromptString" in data else None,
            data["resolvedSearchType"] if "resolvedSearchType" in data else None,
            data["autoDate"] if "autoDate" in data else None,
            cost_dollars=cost_dollars,
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
        user_location: Optional[str] = None,
        livecrawl_timeout: Optional[int] = None,
        livecrawl: Optional[LIVECRAWL_OPTIONS] = None,
        filter_empty_results: Optional[bool] = None,
        subpages: Optional[int] = None,
        subpage_target: Optional[Union[str, List[str]]] = None,
        extras: Optional[ExtrasOptions] = None,
    ) -> SearchResponse[ResultWithText]: ...

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
        subpage_target: Optional[Union[str, List[str]]] = None,
        extras: Optional[ExtrasOptions] = None,
    ) -> SearchResponse[ResultWithText]: ...

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
        user_location: Optional[str] = None,
        livecrawl_timeout: Optional[int] = None,
        livecrawl: Optional[LIVECRAWL_OPTIONS] = None,
        filter_empty_results: Optional[bool] = None,
        extras: Optional[ExtrasOptions] = None,
    ) -> SearchResponse[ResultWithHighlights]: ...

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
        user_location: Optional[str] = None,
        livecrawl_timeout: Optional[int] = None,
        livecrawl: Optional[LIVECRAWL_OPTIONS] = None,
        filter_empty_results: Optional[bool] = None,
        extras: Optional[ExtrasOptions] = None,
    ) -> SearchResponse[ResultWithTextAndHighlights]: ...

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
        user_location: Optional[str] = None,
        livecrawl_timeout: Optional[int] = None,
        livecrawl: Optional[LIVECRAWL_OPTIONS] = None,
        filter_empty_results: Optional[bool] = None,
        extras: Optional[ExtrasOptions] = None,
    ) -> SearchResponse[ResultWithSummary]: ...

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
        user_location: Optional[str] = None,
        livecrawl_timeout: Optional[int] = None,
        livecrawl: Optional[LIVECRAWL_OPTIONS] = None,
        filter_empty_results: Optional[bool] = None,
        extras: Optional[ExtrasOptions] = None,
    ) -> SearchResponse[ResultWithTextAndSummary]: ...

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
        user_location: Optional[str] = None,
        livecrawl_timeout: Optional[int] = None,
        livecrawl: Optional[LIVECRAWL_OPTIONS] = None,
        filter_empty_results: Optional[bool] = None,
        extras: Optional[ExtrasOptions] = None,
    ) -> SearchResponse[ResultWithHighlightsAndSummary]: ...

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
        user_location: Optional[str] = None,
        livecrawl_timeout: Optional[int] = None,
        livecrawl: Optional[LIVECRAWL_OPTIONS] = None,
        subpages: Optional[int] = None,
        subpage_target: Optional[Union[str, List[str]]] = None,
        filter_empty_results: Optional[bool] = None,
        extras: Optional[ExtrasOptions] = None,
    ) -> SearchResponse[ResultWithTextAndHighlightsAndSummary]: ...

    def search_and_contents(self, query: str, **kwargs):
        options = {"query": query}
        for k, v in kwargs.items():
            if v is not None:
                options[k] = v
        # If user didn't ask for any particular content, default to text
        if (
            "text" not in options
            and "highlights" not in options
            and "summary" not in options
            and "extras" not in options
        ):
            options["text"] = True

        merged_options = {}
        merged_options.update(SEARCH_OPTIONS_TYPES)
        merged_options.update(CONTENTS_OPTIONS_TYPES)
        merged_options.update(CONTENTS_ENDPOINT_OPTIONS_TYPES)
        validate_search_options(options, merged_options)

        # Convert schema if present in summary options
        if "summary" in options and isinstance(options["summary"], dict):
            summary_opts = options["summary"]
            if "schema" in summary_opts:
                summary_opts["schema"] = _convert_schema_input(summary_opts["schema"])

        # Nest the appropriate fields under "contents"
        options = nest_fields(
            options,
            [
                "text",
                "highlights",
                "summary",
                "context",
                "subpages",
                "subpage_target",
                "livecrawl",
                "livecrawl_timeout",
                "extras",
            ],
            "contents",
        )
        options = to_camel_case(options, skip_keys=["schema"])
        data = self.request("/search", options)
        cost_dollars = parse_cost_dollars(data.get("costDollars"))
        results = []
        for result in data["results"]:
            snake_result = to_snake_case(result)
            results.append(
                Result(
                    url=snake_result.get("url"),
                    id=snake_result.get("id"),
                    title=snake_result.get("title"),
                    score=snake_result.get("score"),
                    published_date=snake_result.get("published_date"),
                    author=snake_result.get("author"),
                    image=snake_result.get("image"),
                    favicon=snake_result.get("favicon"),
                    subpages=snake_result.get("subpages"),
                    extras=snake_result.get("extras"),
                    text=snake_result.get("text"),
                    highlights=snake_result.get("highlights"),
                    highlight_scores=snake_result.get("highlight_scores"),
                    summary=snake_result.get("summary"),
                )
            )
        return SearchResponse(
            results,
            data["autopromptString"] if "autopromptString" in data else None,
            data["resolvedSearchType"] if "resolvedSearchType" in data else None,
            data["autoDate"] if "autoDate" in data else None,
            context=data.get("context"),
            cost_dollars=cost_dollars,
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
    ) -> SearchResponse[ResultWithText]: ...

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
    ) -> SearchResponse[ResultWithText]: ...

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
    ) -> SearchResponse[ResultWithHighlights]: ...

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
    ) -> SearchResponse[ResultWithTextAndHighlights]: ...

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
    ) -> SearchResponse[ResultWithSummary]: ...

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
    ) -> SearchResponse[ResultWithTextAndSummary]: ...

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
    ) -> SearchResponse[ResultWithHighlightsAndSummary]: ...

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
    ) -> SearchResponse[ResultWithTextAndHighlightsAndSummary]: ...

    def get_contents(self, urls: Union[str, List[str], List[_Result]], **kwargs):
        options = {"urls": urls}
        for k, v in kwargs.items():
            if k != "self" and v is not None:
                options[k] = v

        if (
            "text" not in options
            and "highlights" not in options
            and "summary" not in options
            and "extras" not in options
        ):
            options["text"] = True

        merged_options = {}
        merged_options.update(CONTENTS_OPTIONS_TYPES)
        merged_options.update(CONTENTS_ENDPOINT_OPTIONS_TYPES)
        validate_search_options(options, merged_options)

        # Convert schema if present in summary options
        if "summary" in options and isinstance(options["summary"], dict):
            summary_opts = options["summary"]
            if "schema" in summary_opts:
                summary_opts["schema"] = _convert_schema_input(summary_opts["schema"])

        options = to_camel_case(options, ["schema"])
        data = self.request("/contents", options)
        cost_dollars = parse_cost_dollars(data.get("costDollars"))
        statuses = []
        for status in data.get("statuses", []):
            statuses.append(
                ContentStatus(
                    id=status.get("id"),
                    status=status.get("status"),
                    source=status.get("source"),
                )
            )
        results = []
        for result in data["results"]:
            snake_result = to_snake_case(result)
            results.append(
                Result(
                    url=snake_result.get("url"),
                    id=snake_result.get("id"),
                    title=snake_result.get("title"),
                    score=snake_result.get("score"),
                    published_date=snake_result.get("published_date"),
                    author=snake_result.get("author"),
                    image=snake_result.get("image"),
                    favicon=snake_result.get("favicon"),
                    subpages=snake_result.get("subpages"),
                    extras=snake_result.get("extras"),
                    text=snake_result.get("text"),
                    highlights=snake_result.get("highlights"),
                    highlight_scores=snake_result.get("highlight_scores"),
                    summary=snake_result.get("summary"),
                )
            )
        return SearchResponse(
            results,
            data.get("autopromptString"),
            data.get("resolvedSearchType"),
            data.get("autoDate"),
            context=data.get("context"),
            cost_dollars=cost_dollars,
            statuses=statuses,
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
        cost_dollars = parse_cost_dollars(data.get("costDollars"))
        results = []
        for result in data["results"]:
            snake_result = to_snake_case(result)
            results.append(
                Result(
                    url=snake_result.get("url"),
                    id=snake_result.get("id"),
                    title=snake_result.get("title"),
                    score=snake_result.get("score"),
                    published_date=snake_result.get("published_date"),
                    author=snake_result.get("author"),
                    image=snake_result.get("image"),
                    favicon=snake_result.get("favicon"),
                    subpages=snake_result.get("subpages"),
                    extras=snake_result.get("extras"),
                    text=snake_result.get("text"),
                    highlights=snake_result.get("highlights"),
                    highlight_scores=snake_result.get("highlight_scores"),
                    summary=snake_result.get("summary"),
                )
            )
        return SearchResponse(
            results,
            data.get("autopromptString"),
            data.get("resolvedSearchType"),
            data.get("autoDate"),
            cost_dollars=cost_dollars,
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
    ) -> SearchResponse[ResultWithText]: ...

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
    ) -> SearchResponse[ResultWithText]: ...

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
    ) -> SearchResponse[ResultWithHighlights]: ...

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
    ) -> SearchResponse[ResultWithTextAndHighlights]: ...

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
    ) -> SearchResponse[ResultWithSummary]: ...

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
    ) -> SearchResponse[ResultWithTextAndSummary]: ...

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
    ) -> SearchResponse[ResultWithHighlightsAndSummary]: ...

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
    ) -> SearchResponse[ResultWithTextAndHighlightsAndSummary]: ...

    def find_similar_and_contents(self, url: str, **kwargs):
        options = {"url": url}
        for k, v in kwargs.items():
            if v is not None:
                options[k] = v
        # Default to text if none specified
        if (
            "text" not in options
            and "highlights" not in options
            and "summary" not in options
        ):
            options["text"] = True

        merged_options = {}
        merged_options.update(FIND_SIMILAR_OPTIONS_TYPES)
        merged_options.update(CONTENTS_OPTIONS_TYPES)
        merged_options.update(CONTENTS_ENDPOINT_OPTIONS_TYPES)
        validate_search_options(options, merged_options)

        # Convert schema if present in summary options
        if "summary" in options and isinstance(options["summary"], dict):
            summary_opts = options["summary"]
            if "schema" in summary_opts:
                summary_opts["schema"] = _convert_schema_input(summary_opts["schema"])

        # We nest the content fields
        options = nest_fields(
            options,
            [
                "text",
                "highlights",
                "summary",
                "context",
                "subpages",
                "subpage_target",
                "livecrawl",
                "livecrawl_timeout",
                "extras",
            ],
            "contents",
        )
        options = to_camel_case(options, skip_keys=["schema"])
        data = self.request("/findSimilar", options)
        cost_dollars = parse_cost_dollars(data.get("costDollars"))
        results = []
        for result in data["results"]:
            snake_result = to_snake_case(result)
            results.append(
                Result(
                    url=snake_result.get("url"),
                    id=snake_result.get("id"),
                    title=snake_result.get("title"),
                    score=snake_result.get("score"),
                    published_date=snake_result.get("published_date"),
                    author=snake_result.get("author"),
                    image=snake_result.get("image"),
                    favicon=snake_result.get("favicon"),
                    subpages=snake_result.get("subpages"),
                    extras=snake_result.get("extras"),
                    text=snake_result.get("text"),
                    highlights=snake_result.get("highlights"),
                    highlight_scores=snake_result.get("highlight_scores"),
                    summary=snake_result.get("summary"),
                )
            )
        return SearchResponse(
            results,
            data.get("autopromptString"),
            data.get("resolvedSearchType"),
            data.get("autoDate"),
            context=data.get("context"),
            cost_dollars=cost_dollars,
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

            create_kwargs = {"model": model}
            create_kwargs.update(openai_kwargs)

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
        exa_result = self.search_and_contents(
            query=query,
            num_results=exa_kwargs.get("num_results"),
            include_domains=exa_kwargs.get("include_domains"),
            exclude_domains=exa_kwargs.get("exclude_domains"),
            highlights=exa_kwargs.get("highlights"),
            start_crawl_date=exa_kwargs.get("start_crawl_date"),
            end_crawl_date=exa_kwargs.get("end_crawl_date"),
            start_published_date=exa_kwargs.get("start_published_date"),
            end_published_date=exa_kwargs.get("end_published_date"),
            include_text=exa_kwargs.get("include_text"),
            exclude_text=exa_kwargs.get("exclude_text"),
            use_autoprompt=exa_kwargs.get("use_autoprompt"),
            type=exa_kwargs.get("type"),
            category=exa_kwargs.get("category"),
            flags=exa_kwargs.get("flags"),
        )
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
        stream: Optional[bool] = False,
        text: Optional[bool] = False,
        system_prompt: Optional[str] = None,
        model: Optional[Literal["exa", "exa-pro"]] = None,
        output_schema: Optional[JSONSchemaInput] = None,
        user_location: Optional[str] = None,
    ) -> Union[AnswerResponse, StreamAnswerResponse]: ...

    def answer(
        self,
        query: str,
        *,
        stream: Optional[bool] = False,
        text: Optional[bool] = False,
        system_prompt: Optional[str] = None,
        model: Optional[Literal["exa", "exa-pro"]] = None,
        output_schema: Optional[JSONSchemaInput] = None,
        user_location: Optional[str] = None,
    ) -> Union[AnswerResponse, StreamAnswerResponse]:
        """Generate an answer to a query using Exa's search and LLM capabilities.

        Args:
            query (str): The query to answer.
            text (bool, optional): Whether to include full text in the results. Defaults to False.
            system_prompt (str, optional): A system prompt to guide the LLM's behavior when generating the answer.
            model (str, optional): The model to use for answering. Defaults to None.
            output_schema (dict[str, Any], optional): JSON schema describing the desired answer structure.

        Returns:
            AnswerResponse: An object containing the answer and citations.

        Raises:
            ValueError: If stream=True is provided. Use stream_answer() instead for streaming responses.
        """
        if stream:
            raise ValueError(
                "stream=True is not supported in `answer()`. "
                "Please use `stream_answer(...)` for streaming."
            )

        options = {k: v for k, v in locals().items() if k != "self" and v is not None}

        # Convert output_schema if present
        if "output_schema" in options and options["output_schema"] is not None:
            options["output_schema"] = _convert_schema_input(options["output_schema"])

        options = to_camel_case(options, ["output_schema"])
        response = self.request("/answer", options)

        citations = []
        for result in response["citations"]:
            snake_result = to_snake_case(result)
            citations.append(
                AnswerResult(
                    id=snake_result.get("id"),
                    url=snake_result.get("url"),
                    title=snake_result.get("title"),
                    published_date=snake_result.get("published_date"),
                    author=snake_result.get("author"),
                    text=snake_result.get("text"),
                )
            )
        return AnswerResponse(response["answer"], citations)

    def stream_answer(
        self,
        query: str,
        *,
        text: bool = False,
        system_prompt: Optional[str] = None,
        model: Optional[Literal["exa", "exa-pro"]] = None,
        output_schema: Optional[JSONSchemaInput] = None,
        user_location: Optional[str] = None,
    ) -> StreamAnswerResponse:
        """Generate a streaming answer response.

        Args:
            query (str): The query to answer.
            text (bool): Whether to include full text in the results. Defaults to False.
            system_prompt (str, optional): A system prompt to guide the LLM's behavior when generating the answer.
            model (str, optional): The model to use for answering. Defaults to None.
            output_schema (dict[str, Any], optional): JSON schema describing the desired answer structure.
        Returns:
            StreamAnswerResponse: An object that can be iterated over to retrieve (partial text, partial citations).
                Each iteration yields a tuple of (Optional[str], Optional[List[AnswerResult]]).
        """
        options = {k: v for k, v in locals().items() if k != "self" and v is not None}

        # Convert output_schema if present
        if "output_schema" in options and options["output_schema"] is not None:
            options["output_schema"] = _convert_schema_input(options["output_schema"])

        options = to_camel_case(options, skip_keys=["output_schema"])
        options["stream"] = True
        raw_response = self.request("/answer", options)
        return StreamAnswerResponse(raw_response)


class AsyncExa(Exa):
    def __init__(self, api_key: str, api_base: str = "https://api.exa.ai"):
        super().__init__(api_key, api_base)
        # Override the synchronous ResearchClient with its async counterpart.
        self.research = AsyncResearchClient(self)
        # Override the synchronous WebsetsClient with its async counterpart.
        self.websets = AsyncWebsetsClient(self)
        self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        # this may only be a
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url, headers=self.headers, timeout=600
            )
        return self._client

    async def async_request(
        self, endpoint: str, data=None, method: str = "POST", params=None,
        headers: Optional[Dict[str, str]] = None
    ):
        """Send a request to the Exa API, optionally streaming if data['stream'] is True.

        Args:
            endpoint (str): The API endpoint (path).
            data (dict, optional): The JSON payload to send.
            method (str, optional): The HTTP method to use. Defaults to "POST".
            params (dict, optional): Query parameters.
            headers (Dict[str, str], optional): Additional headers to include in the request. Defaults to None.

        Returns:
            Union[dict, httpx.Response]: If streaming, returns the Response object.
            Otherwise, returns the JSON-decoded response as a dict.

        Raises:
            ValueError: If the request fails (non-200 status code).
        """
        # Check if we need streaming (either from data for POST or params for GET)
        needs_streaming = (data and isinstance(data, dict) and data.get("stream")) or (
            params and params.get("stream") == "true"
        )

        # Merge additional headers with existing headers
        request_headers = {**self.headers}
        if headers:
            request_headers.update(headers)

        if method.upper() == "GET":
            if needs_streaming:
                request = httpx.Request(
                    "GET", self.base_url + endpoint, params=params, headers=request_headers
                )
                res = await self.client.send(request, stream=True)
                return res
            else:
                res = await self.client.get(
                    self.base_url + endpoint, params=params, headers=request_headers
                )
        elif method.upper() == "POST":
            if needs_streaming:
                request = httpx.Request(
                    "POST", self.base_url + endpoint, json=data, headers=request_headers
                )
                res = await self.client.send(request, stream=True)
                return res
            else:
                res = await self.client.post(
                    self.base_url + endpoint, json=data, headers=request_headers
                )
        if res.status_code != 200 and res.status_code != 201:
            raise ValueError(
                f"Request failed with status code {res.status_code}: {res.text}"
            )
        return res.json()

    async def search(
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
        user_location: Optional[str] = None,
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
            type (str, optional): 'keyword', 'neural', 'hybrid', 'fast', or 'auto' (default 'auto').
            category (str, optional): e.g. 'company'
            flags (List[str], optional): Experimental flags for Exa usage.
            moderation (bool, optional): If True, the search results will be moderated for safety.
            user_location (str, optional): Two-letter ISO country code of the user (e.g. US).

        Returns:
            SearchResponse: The response containing search results, etc.
        """
        options = {k: v for k, v in locals().items() if k != "self" and v is not None}
        validate_search_options(options, SEARCH_OPTIONS_TYPES)
        options = to_camel_case(options)
        data = await self.async_request("/search", options)
        cost_dollars = parse_cost_dollars(data.get("costDollars"))
        results = []
        for result in data["results"]:
            snake_result = to_snake_case(result)
            results.append(
                Result(
                    url=snake_result.get("url"),
                    id=snake_result.get("id"),
                    title=snake_result.get("title"),
                    score=snake_result.get("score"),
                    published_date=snake_result.get("published_date"),
                    author=snake_result.get("author"),
                    image=snake_result.get("image"),
                    favicon=snake_result.get("favicon"),
                    subpages=snake_result.get("subpages"),
                    extras=snake_result.get("extras"),
                    text=snake_result.get("text"),
                    highlights=snake_result.get("highlights"),
                    highlight_scores=snake_result.get("highlight_scores"),
                    summary=snake_result.get("summary"),
                )
            )
        return SearchResponse(
            results,
            data["autopromptString"] if "autopromptString" in data else None,
            data["resolvedSearchType"] if "resolvedSearchType" in data else None,
            data["autoDate"] if "autoDate" in data else None,
            cost_dollars=cost_dollars,
        )

    async def search_and_contents(self, query: str, **kwargs):
        options = {"query": query}
        for k, v in kwargs.items():
            if v is not None:
                options[k] = v
        # If user didn't ask for any particular content, default to text
        if (
            "text" not in options
            and "highlights" not in options
            and "summary" not in options
            and "extras" not in options
        ):
            options["text"] = True

        merged_options = {}
        merged_options.update(SEARCH_OPTIONS_TYPES)
        merged_options.update(CONTENTS_OPTIONS_TYPES)
        merged_options.update(CONTENTS_ENDPOINT_OPTIONS_TYPES)
        validate_search_options(options, merged_options)

        # Convert schema if present in summary options
        if "summary" in options and isinstance(options["summary"], dict):
            summary_opts = options["summary"]
            if "schema" in summary_opts:
                summary_opts["schema"] = _convert_schema_input(summary_opts["schema"])

        # Nest the appropriate fields under "contents"
        options = nest_fields(
            options,
            [
                "text",
                "highlights",
                "summary",
                "context",
                "subpages",
                "subpage_target",
                "livecrawl",
                "livecrawl_timeout",
                "extras",
            ],
            "contents",
        )
        options = to_camel_case(options, skip_keys=["schema"])
        data = await self.async_request("/search", options)
        cost_dollars = parse_cost_dollars(data.get("costDollars"))
        results = []
        for result in data["results"]:
            snake_result = to_snake_case(result)
            results.append(
                Result(
                    url=snake_result.get("url"),
                    id=snake_result.get("id"),
                    title=snake_result.get("title"),
                    score=snake_result.get("score"),
                    published_date=snake_result.get("published_date"),
                    author=snake_result.get("author"),
                    image=snake_result.get("image"),
                    favicon=snake_result.get("favicon"),
                    subpages=snake_result.get("subpages"),
                    extras=snake_result.get("extras"),
                    text=snake_result.get("text"),
                    highlights=snake_result.get("highlights"),
                    highlight_scores=snake_result.get("highlight_scores"),
                    summary=snake_result.get("summary"),
                )
            )
        return SearchResponse(
            results,
            data["autopromptString"] if "autopromptString" in data else None,
            data["resolvedSearchType"] if "resolvedSearchType" in data else None,
            data["autoDate"] if "autoDate" in data else None,
            context=data.get("context"),
            cost_dollars=cost_dollars,
        )

    async def get_contents(self, urls: Union[str, List[str], List[_Result]], **kwargs):
        options = {"urls": urls}
        for k, v in kwargs.items():
            if k != "self" and v is not None:
                options[k] = v

        if (
            "text" not in options
            and "highlights" not in options
            and "summary" not in options
            and "extras" not in options
        ):
            options["text"] = True

        merged_options = {}
        merged_options.update(CONTENTS_OPTIONS_TYPES)
        merged_options.update(CONTENTS_ENDPOINT_OPTIONS_TYPES)
        validate_search_options(options, merged_options)

        # Convert schema if present in summary options
        if "summary" in options and isinstance(options["summary"], dict):
            summary_opts = options["summary"]
            if "schema" in summary_opts:
                summary_opts["schema"] = _convert_schema_input(summary_opts["schema"])

        options = to_camel_case(options, ["schema"])
        data = await self.async_request("/contents", options)
        cost_dollars = parse_cost_dollars(data.get("costDollars"))
        statuses = []
        for status in data.get("statuses", []):
            statuses.append(
                ContentStatus(
                    id=status.get("id"),
                    status=status.get("status"),
                    source=status.get("source"),
                )
            )
        results = []
        for result in data["results"]:
            snake_result = to_snake_case(result)
            results.append(
                Result(
                    url=snake_result.get("url"),
                    id=snake_result.get("id"),
                    title=snake_result.get("title"),
                    score=snake_result.get("score"),
                    published_date=snake_result.get("published_date"),
                    author=snake_result.get("author"),
                    image=snake_result.get("image"),
                    favicon=snake_result.get("favicon"),
                    subpages=snake_result.get("subpages"),
                    extras=snake_result.get("extras"),
                    text=snake_result.get("text"),
                    highlights=snake_result.get("highlights"),
                    highlight_scores=snake_result.get("highlight_scores"),
                    summary=snake_result.get("summary"),
                )
            )
        return SearchResponse(
            results,
            data.get("autopromptString"),
            data.get("resolvedSearchType"),
            data.get("autoDate"),
            context=data.get("context"),
            cost_dollars=cost_dollars,
            statuses=statuses,
        )

    async def find_similar(
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
        data = await self.async_request("/findSimilar", options)
        cost_dollars = parse_cost_dollars(data.get("costDollars"))
        results = []
        for result in data["results"]:
            snake_result = to_snake_case(result)
            results.append(
                Result(
                    url=snake_result.get("url"),
                    id=snake_result.get("id"),
                    title=snake_result.get("title"),
                    score=snake_result.get("score"),
                    published_date=snake_result.get("published_date"),
                    author=snake_result.get("author"),
                    image=snake_result.get("image"),
                    favicon=snake_result.get("favicon"),
                    subpages=snake_result.get("subpages"),
                    extras=snake_result.get("extras"),
                    text=snake_result.get("text"),
                    highlights=snake_result.get("highlights"),
                    highlight_scores=snake_result.get("highlight_scores"),
                    summary=snake_result.get("summary"),
                )
            )
        return SearchResponse(
            results,
            data.get("autopromptString"),
            data.get("resolvedSearchType"),
            data.get("autoDate"),
            cost_dollars=cost_dollars,
        )

    async def find_similar_and_contents(self, url: str, **kwargs):
        options = {"url": url}
        for k, v in kwargs.items():
            if v is not None:
                options[k] = v
        # Default to text if none specified
        if (
            "text" not in options
            and "highlights" not in options
            and "summary" not in options
        ):
            options["text"] = True

        merged_options = {}
        merged_options.update(FIND_SIMILAR_OPTIONS_TYPES)
        merged_options.update(CONTENTS_OPTIONS_TYPES)
        merged_options.update(CONTENTS_ENDPOINT_OPTIONS_TYPES)
        validate_search_options(options, merged_options)

        # Convert schema if present in summary options
        if "summary" in options and isinstance(options["summary"], dict):
            summary_opts = options["summary"]
            if "schema" in summary_opts:
                summary_opts["schema"] = _convert_schema_input(summary_opts["schema"])

        # We nest the content fields
        options = nest_fields(
            options,
            [
                "text",
                "highlights",
                "summary",
                "context",
                "subpages",
                "subpage_target",
                "livecrawl",
                "livecrawl_timeout",
                "extras",
            ],
            "contents",
        )
        options = to_camel_case(options, skip_keys=["schema"])
        data = await self.async_request("/findSimilar", options)
        cost_dollars = parse_cost_dollars(data.get("costDollars"))
        results = []
        for result in data["results"]:
            snake_result = to_snake_case(result)
            results.append(
                Result(
                    url=snake_result.get("url"),
                    id=snake_result.get("id"),
                    title=snake_result.get("title"),
                    score=snake_result.get("score"),
                    published_date=snake_result.get("published_date"),
                    author=snake_result.get("author"),
                    image=snake_result.get("image"),
                    favicon=snake_result.get("favicon"),
                    subpages=snake_result.get("subpages"),
                    extras=snake_result.get("extras"),
                    text=snake_result.get("text"),
                    highlights=snake_result.get("highlights"),
                    highlight_scores=snake_result.get("highlight_scores"),
                    summary=snake_result.get("summary"),
                )
            )
        return SearchResponse(
            results,
            data.get("autopromptString"),
            data.get("resolvedSearchType"),
            data.get("autoDate"),
            context=data.get("context"),
            cost_dollars=cost_dollars,
        )

    async def answer(
        self,
        query: str,
        *,
        stream: Optional[bool] = False,
        text: Optional[bool] = False,
        system_prompt: Optional[str] = None,
        model: Optional[Literal["exa", "exa-pro"]] = None,
        output_schema: Optional[JSONSchemaInput] = None,
        user_location: Optional[str] = None,
    ) -> Union[AnswerResponse, StreamAnswerResponse]:
        """Generate an answer to a query using Exa's search and LLM capabilities.

        Args:
            query (str): The query to answer.
            text (bool, optional): Whether to include full text in the results. Defaults to False.
            system_prompt (str, optional): A system prompt to guide the LLM's behavior when generating the answer.
            model (str, optional): The model to use for answering. Defaults to None.
            output_schema (dict[str, Any], optional): JSON schema describing the desired answer structure.

        Returns:
            AnswerResponse: An object containing the answer and citations.

        Raises:
            ValueError: If stream=True is provided. Use stream_answer() instead for streaming responses.
        """
        if stream:
            raise ValueError(
                "stream=True is not supported in `answer()`. "
                "Please use `stream_answer(...)` for streaming."
            )

        options = {k: v for k, v in locals().items() if k != "self" and v is not None}

        # Convert output_schema if present
        if "output_schema" in options and options["output_schema"] is not None:
            options["output_schema"] = _convert_schema_input(options["output_schema"])

        options = to_camel_case(options, skip_keys=["output_schema"])
        response = await self.async_request("/answer", options)

        citations = []
        for result in response["citations"]:
            snake_result = to_snake_case(result)
            citations.append(
                AnswerResult(
                    id=snake_result.get("id"),
                    url=snake_result.get("url"),
                    title=snake_result.get("title"),
                    published_date=snake_result.get("published_date"),
                    author=snake_result.get("author"),
                    text=snake_result.get("text"),
                )
            )
        return AnswerResponse(response["answer"], citations)

    async def stream_answer(
        self,
        query: str,
        *,
        text: bool = False,
        system_prompt: Optional[str] = None,
        model: Optional[Literal["exa", "exa-pro"]] = None,
        output_schema: Optional[JSONSchemaInput] = None,
    ) -> AsyncStreamAnswerResponse:
        """Generate a streaming answer response.

        Args:
            query (str): The query to answer.
            text (bool): Whether to include full text in the results. Defaults to False.
            system_prompt (str, optional): A system prompt to guide the LLM's behavior when generating the answer.
            model (str, optional): The model to use for answering. Defaults to None.
            output_schema (dict[str, Any], optional): JSON schema describing the desired answer structure.
        Returns:
            AsyncStreamAnswerResponse: An object that can be iterated over to retrieve (partial text, partial citations).
                Each iteration yields a tuple of (Optional[str], Optional[List[AnswerResult]]).
        """
        options = {k: v for k, v in locals().items() if k != "self" and v is not None}

        # Convert output_schema if present
        if "output_schema" in options and options["output_schema"] is not None:
            options["output_schema"] = _convert_schema_input(options["output_schema"])

        options = to_camel_case(options, skip_keys=["output_schema"])
        options["stream"] = True
        raw_response = await self.async_request("/answer", options)
        return AsyncStreamAnswerResponse(raw_response)
