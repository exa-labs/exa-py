from __future__ import annotations

import dataclasses
import json
import math
import os
import re
import threading
from dataclasses import dataclass
from functools import wraps
from typing import (
    Any,
    AsyncIterator,
    Callable,
    Dict,
    Generic,
    Iterable,
    Iterator,
    List,
    Literal,
    Mapping,
    Optional,
    Sequence,
    TypeVar,
    Union,
    cast,
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
from types import TracebackType
from typing_extensions import NotRequired, Self, TypedDict, deprecated

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
from .monitors import SearchMonitorsClient, AsyncSearchMonitorsClient
from .research import ResearchClient, AsyncResearchClient
from .agent import AgentNamespace, AsyncAgentNamespace, BetaClient, AsyncBetaClient
from .agent.betas import headers_for_betas
from .errors import ExaTimeoutError as ExaTimeoutError
from .errors import reporting_failover_connect_timeouts, typed_timeouts
from .request_options import merge_body, merge_headers, merge_query
from .tools import (
    AsyncAnthropicNamespace,
    AsyncOpenAINamespace,
    AsyncToolNamespace,
    AnthropicNamespace,
    OpenAINamespace,
    ToolNamespace,
    _ToolRegistry,
)
from .api_warnings import issue_body_warnings, warn_deprecated_fields


is_beta = os.getenv("IS_BETA") == "True"

# Default max characters for text contents
DEFAULT_MAX_CHARACTERS = 10_000

# Default HTTP request timeout in seconds
DEFAULT_REQUEST_TIMEOUT = 600.0

# Arguments of the search, contents and answer methods that configure the
# request instead of describing the API payload.
_NON_BODY_ARGUMENTS = frozenset(
    {"self", "timeout", "extra_headers", "extra_query", "extra_body"}
)


def _validate_timeout(timeout: Optional[float]) -> Optional[float]:
    """Use the same positive finite timeout range for Requests and HTTPX.

    The upper bound is `threading.TIMEOUT_MAX`, the longest wait Python
    supports on the platform: with a longer timeout, Requests would raise
    OverflowError on every request.
    """
    if timeout is not None and (
        isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or not math.isfinite(timeout)
        or timeout <= 0
        or timeout > threading.TIMEOUT_MAX
    ):
        raise ValueError("timeout must be a positive, finite number of seconds or None")
    return timeout


# Longest snippet of a non-JSON response body to include in an error message.
_NON_JSON_BODY_SNIPPET_LENGTH = 500


def _decode_json_body(res: Union[requests.Response, httpx.Response]) -> Any:
    """Return the decoded JSON body of a successful API response.

    A proxy or gateway in front of the API can answer with an HTML or plain-text
    page and a 2xx status. Decoding that body raises a JSONDecodeError that names
    neither the status nor the body, so the error raised here carries both.

    Raises:
        ValueError: If the body is empty or not valid JSON. The message has the
            status code and up to 500 characters of the body.
    """
    try:
        return res.json()
    except ValueError as error:
        body = " ".join(res.text.split())
        if not body:
            message = (
                "Expected a JSON response but received an empty body "
                f"(status {res.status_code})."
            )
        else:
            if len(body) > _NON_JSON_BODY_SNIPPET_LENGTH:
                body = body[:_NON_JSON_BODY_SNIPPET_LENGTH] + "…"
            message = (
                "Expected a JSON response but received a non-JSON body "
                f"(status {res.status_code}): {body}"
            )
        raise ValueError(message) from error


def _is_json_content_type(content_type: Any) -> bool:
    """Whether a ``Content-Type`` value names JSON.

    That is ``application/json`` or a ``+json`` media type, with any parameters.
    """
    if not isinstance(content_type, str):
        return False
    media_type = content_type.split(";", 1)[0].strip().lower()
    return media_type == "application/json" or media_type.endswith("+json")


def _is_json_response(response: Any) -> bool:
    """Whether a streamed response arrived whole as JSON instead of as an event stream.

    A response object without headers is read as an event stream, as before
    this check existed.
    """
    headers = getattr(response, "headers", None)
    return headers is not None and _is_json_content_type(headers.get("content-type"))


# Exa-Beta token required for Dynamic Highlights (research preview).
DYNAMIC_HIGHLIGHTS_BETA = "dynamic-highlights-2026-08-28"


def _convert_contents_summary_schema(options: Dict[str, Any]) -> None:
    contents = options.get("contents")
    if not isinstance(contents, dict):
        return

    summary_opts = contents.get("summary")
    if isinstance(summary_opts, dict) and "schema" in summary_opts:
        summary_opts["schema"] = _convert_schema_input(summary_opts["schema"])


def _merge_search_body(
    body: Dict[str, Any], extra_body: Optional[Mapping[str, Any]], *, streaming: bool = False
) -> Dict[str, Any]:
    body = {**body, **(extra_body or {})}
    if streaming:
        body["stream"] = True
    else:
        body.pop("stream", None)
    return body


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


def _parse_entities(entities_data: Optional[List[dict]]) -> Optional[List]:
    """
    Parse entity data from API response into Entity dataclasses.

    Handles field mapping for reserved Python keywords:
    - 'from' -> 'from_date'
    - 'to' -> 'to_date'
    """
    if not entities_data:
        return None

    # Import here to avoid circular imports (Entity types defined later in file)
    from exa_py.api import (
        CompanyEntity,
        PersonEntity,
        EntityCompanyProperties,
        EntityPersonProperties,
        EntityCompanyPropertiesWorkforce,
        EntityCompanyPropertiesHeadquarters,
        EntityCompanyPropertiesFinancials,
        EntityCompanyPropertiesFundingRound,
        EntityCompanyPropertiesWebTraffic,
        EntityDateRange,
        EntityPersonPropertiesCompanyRef,
        EntityPersonPropertiesWorkHistoryEntry,
        EntityPersonPropertiesInstitutionRef,
        EntityPersonPropertiesEducationHistoryEntry,
        EntityPersonPropertiesNotableWork,
        EntityPersonPropertiesResearch,
    )

    def parse_date_range(data: Optional[dict]) -> Optional[EntityDateRange]:
        if not data:
            return None
        return EntityDateRange(
            from_date=data.get("from"),
            to_date=data.get("to"),
        )

    def parse_company_ref(data: Optional[dict]) -> Optional[EntityPersonPropertiesCompanyRef]:
        if not data:
            return None
        return EntityPersonPropertiesCompanyRef(
            id=data.get("id"),
            name=data.get("name"),
        )

    def parse_work_history_entry(data: dict) -> EntityPersonPropertiesWorkHistoryEntry:
        return EntityPersonPropertiesWorkHistoryEntry(
            title=data.get("title"),
            location=data.get("location"),
            dates=parse_date_range(data.get("dates")),
            company=parse_company_ref(data.get("company")),
        )

    def parse_institution_ref(data: Optional[dict]) -> Optional[EntityPersonPropertiesInstitutionRef]:
        if not data:
            return None
        return EntityPersonPropertiesInstitutionRef(
            id=data.get("id"),
            name=data.get("name"),
        )

    def parse_education_history_entry(data: dict) -> EntityPersonPropertiesEducationHistoryEntry:
        return EntityPersonPropertiesEducationHistoryEntry(
            degree=data.get("degree"),
            dates=parse_date_range(data.get("dates")),
            institution=parse_institution_ref(data.get("institution")),
        )

    def parse_notable_work(data: dict) -> EntityPersonPropertiesNotableWork:
        return EntityPersonPropertiesNotableWork(
            title=data.get("title"),
            year=data.get("year"),
            venue=data.get("venue"),
            citation_count=data.get("citationCount"),
            doi=data.get("doi"),
            id=data.get("id"),
            type=data.get("type"),
        )

    def parse_research(data: Optional[dict]) -> Optional[EntityPersonPropertiesResearch]:
        if not data:
            return None
        notable_works = data.get("notableWorks")
        return EntityPersonPropertiesResearch(
            works_count=data.get("worksCount"),
            citation_count=data.get("citationCount"),
            h_index=data.get("hIndex"),
            first_publication_year=data.get("firstPublicationYear"),
            latest_publication_year=data.get("latestPublicationYear"),
            areas=data.get("areas"),
            notable_works=[parse_notable_work(nw) for nw in notable_works] if notable_works is not None else None,
        )

    def parse_funding_round(data: Optional[dict]) -> Optional[EntityCompanyPropertiesFundingRound]:
        if not data:
            return None
        return EntityCompanyPropertiesFundingRound(
            name=data.get("name"),
            date=data.get("date"),
            amount=data.get("amount"),
        )

    def parse_financials(data: Optional[dict]) -> Optional[EntityCompanyPropertiesFinancials]:
        if not data:
            return None
        return EntityCompanyPropertiesFinancials(
            revenue_annual=data.get("revenueAnnual"),
            funding_total=data.get("fundingTotal"),
            funding_latest_round=parse_funding_round(data.get("fundingLatestRound")),
        )

    def parse_web_traffic(data: Optional[dict]) -> Optional[EntityCompanyPropertiesWebTraffic]:
        if not data:
            return None
        return EntityCompanyPropertiesWebTraffic(
            visits_monthly=data.get("visitsMonthly"),
        )

    def parse_company_properties(data: dict) -> EntityCompanyProperties:
        workforce_data = data.get("workforce")
        headquarters_data = data.get("headquarters")
        return EntityCompanyProperties(
            name=data.get("name"),
            founded_year=data.get("foundedYear"),
            description=data.get("description"),
            workforce=EntityCompanyPropertiesWorkforce(total=workforce_data.get("total")) if workforce_data else None,
            headquarters=EntityCompanyPropertiesHeadquarters(
                address=headquarters_data.get("address"),
                city=headquarters_data.get("city"),
                postal_code=headquarters_data.get("postalCode"),
                country=headquarters_data.get("country"),
            ) if headquarters_data else None,
            financials=parse_financials(data.get("financials")),
            web_traffic=parse_web_traffic(data.get("webTraffic")),
        )

    def parse_person_properties(data: dict) -> EntityPersonProperties:
        work_history = data.get("workHistory")
        education_history = data.get("educationHistory")
        return EntityPersonProperties(
            name=data.get("name"),
            location=data.get("location"),
            work_history=[parse_work_history_entry(wh) for wh in work_history] if work_history is not None else None,
            first_name=data.get("firstName"),
            last_name=data.get("lastName"),
            education_history=[parse_education_history_entry(eh) for eh in education_history] if education_history is not None else None,
            research=parse_research(data.get("research")),
        )

    entities = []
    for entity_data in entities_data:
        entity_type = entity_data.get("type")
        if entity_type == "company":
            entities.append(CompanyEntity(
                id=entity_data["id"],
                type="company",
                version=entity_data["version"],
                properties=parse_company_properties(entity_data.get("properties", {})),
            ))
        elif entity_type == "person":
            entities.append(PersonEntity(
                id=entity_data["id"],
                type="person",
                version=entity_data["version"],
                properties=parse_person_properties(entity_data.get("properties", {})),
            ))
    return entities if entities else None


# Category options for search filtering
Category = Literal[
    "company",
    "news",
    "publication",
    "personal site",
    "financial report",
    "people",
]
"""Data category to focus on when searching. Each category returns results specialized for that content type."""

# Search type options
SearchType = Literal[
    "auto",
    "fast",
    "deep-lite",
    "deep",
    "deep-reasoning",
    "neural",
    "instant",
    "lite",
]
"""Search type that determines the search algorithm.

We recommend 'lite', 'auto' and 'deep'. 'fast', 'instant' and
'deep-reasoning' are legacy search types. They are still accepted, and each
has an alternative. Use 'lite' instead of 'instant'. Use 'lite' instead of
'fast', or 'auto' when the request needs parameters 'lite' rejects. Instead
of 'deep-reasoning', use 'deep', or Exa Agent for long-running research,
list building and multi-hop enrichment. Start an Exa Agent run with
``exa.agent.runs.create``.

'auto' (default) automatically selects the best approach, 'fast' prioritizes
speed, 'deep-lite', 'deep', and 'deep-reasoning' are deep-search variants,
'neural' uses embedding-based semantic search, and 'instant' uses low-latency
neural search. 'lite' (beta) is a low-cost search that supports a reduced set
of parameters.

Search methods also accept any other string as ``type`` and pass it through
to the API as given.
"""


class DeepTextOutputSchema(TypedDict, total=False):
    """Deep search output schema for plain-text output."""

    type: Literal["text"]
    description: str


class DeepObjectOutputSchema(TypedDict, total=False):
    """Deep search output schema for structured JSON object output."""

    type: Literal["object"]
    properties: Dict[str, Any]
    required: List[str]


DeepOutputSchema = Union[DeepTextOutputSchema, DeepObjectOutputSchema]
"""Search output schema.

- ``{"type": "text", "description": ...}`` returns plain text in ``output.content``.
- ``{"type": "object", ...}`` returns structured JSON in ``output.content``.

For object schemas, the API enforces max nesting depth 2 and max 10 total properties.
"""


class UserLocationCountry(TypedDict):
    """The user's country only. Equivalent to passing the country code as a string.

    Attributes:
        country (str): The two-letter ISO 3166-1 country code of the user, e.g. ``"US"``.
    """

    country: str


class UserLocationCoordinates(TypedDict):
    """The user's coordinates, with an optional country.

    Attributes:
        latitude (float): The user's latitude in decimal degrees, from -90 to 90.
        longitude (float): The user's longitude in decimal degrees, from -180 to 180.
        country (str, optional): The two-letter ISO 3166-1 country code of the user,
            e.g. ``"US"``.
    """

    latitude: float
    longitude: float
    country: NotRequired[str]


UserLocation = Union[UserLocationCountry, UserLocationCoordinates]
"""The end user's location, as a dict with ``country``, a ``latitude`` and
``longitude`` pair, or both.

``user_location`` also takes a two-letter ISO 3166-1 country code string, e.g.
``"US"``. The country localizes results. Coordinates are used only for queries
that name no place but depend on where the user is, such as "coffee near me".
They do not set a country, so send ``country`` with them to localize results.
Send only the precision your use case needs.
"""


def _is_coordinate(value: object, bound: float) -> bool:
    """Whether `value` is a number of decimal degrees from -`bound` to `bound`."""
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and -bound <= value <= bound
    )


def _is_user_location_dict(value: Dict[Any, Any]) -> bool:
    """Whether `value` is a `UserLocationCountry` or a `UserLocationCoordinates`."""
    if not value or not set(value) <= {"country", "latitude", "longitude"}:
        return False
    if "country" in value and not isinstance(value["country"], str):
        return False
    if ("latitude" in value) != ("longitude" in value):
        return False
    return "latitude" not in value or (
        _is_coordinate(value["latitude"], 90) and _is_coordinate(value["longitude"], 180)
    )


def _validate_user_location(user_location: object) -> None:
    """Check a ``user_location`` argument against the forms the API accepts.

    Those are a country code string, ``{"country": str}``, and
    ``{"latitude": number, "longitude": number}`` with an optional
    ``"country": str``, with latitude from -90 to 90 and longitude from -180
    to 180. None means the option is not set. The API checks the country code
    itself.

    Raises:
        ValueError: If `user_location` has another type, another key, or a
            value of another type or range.
    """
    if user_location is None or isinstance(user_location, str):
        return
    if isinstance(user_location, dict) and _is_user_location_dict(user_location):
        return
    raise ValueError(
        f"Invalid value for option 'user_location': {user_location!r}. Expected a "
        "two-letter country code string, a dict with 'country', or a dict with "
        "'latitude' and 'longitude' in decimal degrees and an optional 'country'."
    )


SEARCH_OPTIONS_TYPES = {
    "query": [str],  # The query string.
    "num_results": [int],  # Number of results (Default: 10, Max for basic: 10).
    "include_domains": [
        list
    ],  # Domains to search from; exclusive with 'exclude_domains'.
    "exclude_domains": [list],  # Domains to omit; exclusive with 'include_domains'.
    "start_crawl_date": [
        str
    ],  # DEPRECATED FIELD: will be removed in a future release. Results after this crawl date. ISO 8601 format.
    "end_crawl_date": [
        str
    ],  # DEPRECATED FIELD: will be removed in a future release. Results before this crawl date. ISO 8601 format.
    "start_published_date": [
        str
    ],  # Results after this publish date; excludes links with no date. ISO 8601 format.
    "end_published_date": [
        str
    ],  # Results before this publish date; excludes links with no date. ISO 8601 format.
    "user_location": [
        str,
        dict,
    ],  # The end user's location, as a two-letter ISO 3166-1 country code or a UserLocation dict.
    "include_text": [
        list
    ],  # Must be present in webpage text. (One string, up to 5 words)
    "exclude_text": [
        list
    ],  # Must not be present in webpage text. (One string, up to 5 words)
    "type": [
        SearchType,
        str,
    ],  # Search type: 'auto', 'fast', 'deep-lite', 'deep', 'deep-reasoning', 'neural', 'instant', or 'lite' (Default: auto)
    "category": [str],  # A data category to focus on.
    "flags": [list],  # Experimental flags array for Exa usage.
    "moderation": [bool],  # If true, moderate search results for safety.
    "contents": [dict, bool],  # Options for retrieving page contents
    "additional_queries": [
        list
    ],  # Alternative query formulations for deep search variants (max 5). Only used when type is deep-lite/deep/deep-reasoning.
    "system_prompt": [str],  # Instructions for search planning and final synthesis across all search types.
    "output_schema": [dict],  # Search output schema: {"type":"text"} or {"type":"object", ...}
    "objective": [str],  # The broader goal the search serves, beyond the query itself (max 4096 chars).
    "user_identifier": [str],  # Opaque, non-personal identifier of the end user the request is made for.
    "stream": [bool],  # If true, stream back OpenAI-style chat completion chunks.
}

FIND_SIMILAR_OPTIONS_TYPES = {
    "url": [str],
    "num_results": [int],
    "include_domains": [list],
    "exclude_domains": [list],
    "start_crawl_date": [str],  # DEPRECATED FIELD: will be removed in a future release.
    "end_crawl_date": [str],  # DEPRECATED FIELD: will be removed in a future release.
    "start_published_date": [str],
    "end_published_date": [str],
    "include_text": [list],
    "exclude_text": [list],
    "exclude_source_domain": [bool],
    "category": [str],  # A data category to focus on.
    "flags": [list],  # Experimental flags array for Exa usage.
    "contents": [dict, bool],  # Options for retrieving page contents
}

# Livecrawl options
LIVECRAWL_OPTIONS = Literal["always", "fallback", "never", "auto", "preferred"]

CONTENTS_OPTIONS_TYPES = {
    "urls": [list],
    "text": [dict, bool],
    "summary": [dict, bool],
    "highlights": [dict, bool],
    "context": [dict, bool],  # DEPRECATED FIELD: use highlights or text instead.
    "metadata": [dict, bool],
    "livecrawl_timeout": [int],
    "livecrawl": [LIVECRAWL_OPTIONS],  # DEPRECATED FIELD: use max_age_hours instead.
    "max_age_hours": [int],
    "snapshot_as_of": [str],
    "filter_empty_results": [bool],
    "flags": [list],  # We allow flags to be passed here too
}

CONTENTS_ENDPOINT_OPTIONS_TYPES = {
    "subpages": [int],
    "subpage_target": [str, list],
    "extras": [dict],
    "flags": [list],  # We allow flags to be passed here too
}

# Content options that search_and_contents and find_similar_and_contents accept
# as keyword arguments and send inside the request's ``contents`` object.
NESTED_CONTENTS_FIELDS = [
    "text",
    "summary",
    "highlights",
    "context",  # DEPRECATED FIELD: accepted only for backward compatibility.
    "subpages",
    "subpage_target",
    "livecrawl",
    "livecrawl_timeout",
    "max_age_hours",
    "snapshot_as_of",
    "filter_empty_results",
    "extras",
]

# Fields of the /contents request itself rather than content options: they stay
# at the top level of the body and are not accepted by find_similar.
CONTENTS_REQUEST_OPTIONS_TYPES = {
    "user_identifier": [str],  # Opaque, non-personal identifier of the end user the request is made for.
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
        if key == "user_location":
            # The same check as answer() and stream_answer() make.
            _validate_user_location(value)
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


VERBOSITY_OPTIONS = Literal["compact", "standard", "full"]
"""Verbosity levels for content filtering.
- compact: Most concise output, main content only (default)
- standard: Balanced content with more detail
- full: Complete content including all sections
"""

SECTION_TAG = Literal[
    "unspecified", "header", "navigation", "banner", "body", "sidebar", "footer", "metadata"
]
"""Section tags for semantic content filtering."""


class TextContentsOptions(TypedDict, total=False):
    """A class representing the options that you can specify when requesting text

    Attributes:
        max_characters (int): The maximum number of characters to return. Default: None (no limit).
        include_html_tags (bool): If true, include HTML tags in the returned text. Default false.
        verbosity (VERBOSITY_OPTIONS): Controls verbosity level of returned content.
            "compact" (default): main content only; "standard": balanced; "full": all sections.
            Requires max_age_hours=0 to take effect.
        include_sections (List[SECTION_TAG]): Only include content from these semantic sections.
            Requires max_age_hours=0 to take effect.
        exclude_sections (List[SECTION_TAG]): Exclude content from these semantic sections.
            Requires max_age_hours=0 to take effect.
    """

    max_characters: int
    include_html_tags: bool
    verbosity: VERBOSITY_OPTIONS
    include_sections: List[SECTION_TAG]
    exclude_sections: List[SECTION_TAG]


@deprecated("Use Pydantic models or dict[str, Any] directly instead. JSONSchema will be removed in a future version.")
class JSONSchema(TypedDict, total=False):
    """DEPRECATED TYPE: Legacy JSON Schema TypedDict for structured summary output.

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


class HighlightsContentsOptions(TypedDict, total=False):
    """Overrides for highlight extraction. Prefer ``contents={"highlights": True}``.

    Exa dynamically chooses the number of characters based on each document's
    relevance to your query. No manual character budget is needed for concise
    AI context. Use a fixed limit only when your application explicitly requires one.

    Attributes:
        query (str): The query string for highlight generation. Highlights will be biased towards this query.
        max_characters (int): Override for an explicit application character limit.
            Prefer ``highlights=True`` for relevance-based sizing rather than choosing
            an arbitrary limit to keep context concise. Not compatible with dynamic.
        dynamic (bool): Enable Dynamic Highlights (research preview): allocates one shared context budget
            across all results instead of a per-document budget; the model sizes the output itself.
            Not compatible with max_characters. Beta: requires passing
            ``betas=[DYNAMIC_HIGHLIGHTS_BETA]`` to the request.
        num_sentences (int): Deprecated. Use max_characters.
        highlights_per_url (int): Deprecated. Use max_characters.
    """

    query: str
    max_characters: int
    dynamic: bool
    num_sentences: int  # DEPRECATED FIELD: use max_characters. Do not use in new code.
    highlights_per_url: int  # DEPRECATED FIELD: use max_characters. Do not use in new code.


class ContextContentsOptions(TypedDict, total=False):
    """DEPRECATED TYPE: Options for legacy aggregated context from search results.

    .. deprecated::
        Use ``highlights`` or ``text`` instead. The ``context`` option is deprecated
        and will be removed in a future version.

    Attributes:
        max_characters (int): DEPRECATED FIELD - only applies to deprecated contents.context.
            Use highlights.max_characters or text.max_characters instead.
    """

    max_characters: int  # DEPRECATED FIELD: only for contents.context. Use highlights/text instead.


class ExtrasOptions(TypedDict, total=False):
    """A class representing additional extraction fields (e.g. links, images)"""

    links: int
    image_links: int


class ContentsOptions(TypedDict, total=False):
    """Options for retrieving page contents in search and legacy find_similar methods.

    All fields are optional. If no content options are specified, text with
    max_characters=10000 is returned by default.

    Attributes:
        text (TextContentsOptions | True): Options for text extraction, or True for defaults.
        highlights (HighlightsContentsOptions | True): Recommended: True for AI context,
            RAG, and search previews. Exa dynamically chooses excerpt length based on
            each document's relevance to the query. Read ``result.highlights``.
            Set ``max_characters`` only for an explicit application character limit.
        summary (SummaryContentsOptions | True): Options for summary generation, or True for defaults.
        context (ContextContentsOptions | True): Deprecated. Use ``highlights`` or ``text``.
        max_age_hours (int): Maximum age of cached content in hours. If content is older, it will be
            fetched fresh. Special values: 0 = always fetch fresh content,
            -1 = never fetch fresh (use cached content only). Example: 168 = fetch fresh for pages older than 7 days.
        livecrawl (str): Deprecated. Use ``max_age_hours`` instead. Does not guarantee freshly fetched
            content. Cannot be combined with ``max_age_hours``.
        snapshot_as_of (str): ISO 8601 datetime. Return the newest stored version at or before this instant instead of live content.
        subpages (int): DEPRECATED FIELD - do not use in new code. Subpage crawling on
            search is deprecated. Call ``get_contents(urls, subpages=...)`` instead.
        subpage_target (str | List[str]): DEPRECATED FIELD - do not use in new code.
            Call ``get_contents(urls, subpage_target=...)`` instead.
        extras (ExtrasOptions): Additional extraction options (links, images).
    """

    text: Union[TextContentsOptions, Literal[True]]
    highlights: Union[HighlightsContentsOptions, Literal[True]]
    summary: Union[SummaryContentsOptions, Literal[True]]
    context: Union[ContextContentsOptions, Literal[True]]  # DEPRECATED FIELD: use highlights or text.
    livecrawl: LIVECRAWL_OPTIONS  # DEPRECATED FIELD: use max_age_hours. Cannot be combined with it.
    livecrawl_timeout: int
    max_age_hours: int
    snapshot_as_of: str
    subpages: int  # DEPRECATED FIELD: use get_contents(urls, subpages=...) instead.
    subpage_target: Union[str, List[str]]  # DEPRECATED FIELD: use get_contents(urls, subpage_target=...) instead.
    extras: ExtrasOptions


class CostDollarsSearch(TypedDict, total=False):
    """Represents the cost breakdown for search."""

    neural: float
    keyword: float


class CostDollarsContents(TypedDict, total=False):
    """Represents the cost breakdown for contents."""

    text: float
    summary: float


@dataclass
class CostDollars:
    """Represents costDollars field in the API response."""

    total: float
    search: CostDollarsSearch = None
    contents: CostDollarsContents = None


# Entity types for company/people search results
# Only returned when using category="company" or category="people" searches


@dataclass
class EntityCompanyPropertiesWorkforce:
    """Company workforce information."""

    total: Optional[int] = None


@dataclass
class EntityCompanyPropertiesHeadquarters:
    """Company headquarters information."""

    address: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None


@dataclass
class EntityCompanyPropertiesFundingRound:
    """Funding round information."""

    name: Optional[str] = None
    date: Optional[str] = None
    amount: Optional[int] = None


@dataclass
class EntityCompanyPropertiesFinancials:
    """Company financial information."""

    revenue_annual: Optional[int] = None
    funding_total: Optional[int] = None
    funding_latest_round: Optional[EntityCompanyPropertiesFundingRound] = None


@dataclass
class EntityCompanyPropertiesWebTraffic:
    """Company web traffic information."""

    visits_monthly: Optional[int] = None


@dataclass
class EntityCompanyProperties:
    """Structured properties for a company entity."""

    name: Optional[str] = None
    founded_year: Optional[int] = None
    description: Optional[str] = None
    workforce: Optional[EntityCompanyPropertiesWorkforce] = None
    headquarters: Optional[EntityCompanyPropertiesHeadquarters] = None
    financials: Optional[EntityCompanyPropertiesFinancials] = None
    web_traffic: Optional[EntityCompanyPropertiesWebTraffic] = None


@dataclass
class EntityDateRange:
    """Date range for work history entries."""

    from_date: Optional[str] = None  # API returns 'from' but it's a reserved keyword
    to_date: Optional[str] = None  # API returns 'to', renamed for consistency


@dataclass
class EntityPersonPropertiesCompanyRef:
    """Reference to a company in work history."""

    id: Optional[str] = None
    name: Optional[str] = None


@dataclass
class EntityPersonPropertiesWorkHistoryEntry:
    """A single work history entry for a person."""

    title: Optional[str] = None
    location: Optional[str] = None
    dates: Optional[EntityDateRange] = None
    company: Optional[EntityPersonPropertiesCompanyRef] = None


@dataclass
class EntityPersonPropertiesInstitutionRef:
    """Reference to an institution in education history.

    Attributes:
        id (str, optional): Referenced institution identifier.
        name (str, optional): Referenced institution name.
    """

    id: Optional[str] = None
    name: Optional[str] = None


@dataclass
class EntityPersonPropertiesEducationHistoryEntry:
    """A single education history entry for a person.

    Attributes:
        degree (str, optional): Degree or credential.
        dates (EntityDateRange, optional): Education date range.
        institution (EntityPersonPropertiesInstitutionRef, optional): Education institution.
    """

    degree: Optional[str] = None
    dates: Optional[EntityDateRange] = None
    institution: Optional[EntityPersonPropertiesInstitutionRef] = None


@dataclass
class EntityPersonPropertiesNotableWork:
    """A notable publication by a person.

    Attributes:
        title (str, optional): Publication title.
        year (int, optional): Publication year.
        venue (str, optional): Publication venue.
        citation_count (int, optional): Number of works citing this publication.
        doi (str, optional): Digital Object Identifier.
        id (str, optional): Resolved publication entity identifier, when available.
        type (str, optional): Publication type.
    """

    title: Optional[str] = None
    year: Optional[int] = None
    venue: Optional[str] = None
    citation_count: Optional[int] = None
    doi: Optional[str] = None
    id: Optional[str] = None
    type: Optional[str] = None


@dataclass
class EntityPersonPropertiesResearch:
    """Research information for a person.

    Attributes:
        works_count (int, optional): Lifetime number of works.
        citation_count (int, optional): Lifetime citation count.
        h_index (int, optional): Research h-index.
        first_publication_year (int, optional): Year of the first publication.
        latest_publication_year (int, optional): Year of the latest publication.
        areas (List[str], optional): Ranked research areas, most active first.
        notable_works (List[EntityPersonPropertiesNotableWork], optional): Most-cited notable works.
    """

    works_count: Optional[int] = None
    citation_count: Optional[int] = None
    h_index: Optional[int] = None
    first_publication_year: Optional[int] = None
    latest_publication_year: Optional[int] = None
    areas: Optional[List[str]] = None
    notable_works: Optional[List[EntityPersonPropertiesNotableWork]] = None


@dataclass
class EntityPersonProperties:
    """Structured properties for a person entity.

    Attributes:
        name (str, optional): Person name.
        location (str, optional): Person location.
        work_history (List[EntityPersonPropertiesWorkHistoryEntry], optional): Known professional roles for this person.
        first_name (str, optional): Person first name.
        last_name (str, optional): Person last name.
        education_history (List[EntityPersonPropertiesEducationHistoryEntry], optional): Known education history for this person.
        research (EntityPersonPropertiesResearch, optional): Person research information.
    """

    name: Optional[str] = None
    location: Optional[str] = None
    work_history: Optional[List[EntityPersonPropertiesWorkHistoryEntry]] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    education_history: Optional[List[EntityPersonPropertiesEducationHistoryEntry]] = None
    research: Optional[EntityPersonPropertiesResearch] = None


@dataclass
class CompanyEntity:
    """Structured entity data for a company."""

    id: str
    type: Literal["company"]
    version: int
    properties: EntityCompanyProperties


@dataclass
class PersonEntity:
    """Structured entity data for a person."""

    id: str
    type: Literal["person"]
    version: int
    properties: EntityPersonProperties


Entity = Union[CompanyEntity, PersonEntity]


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
        entities (List[Entity], optional): Structured entity data for company or person searches.
        crawl_date (str, optional): The date the page was last crawled (if available).
        snapshot_at (str, optional): Crawl instant of the stored version served for a snapshotAsOf request.
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
    entities: Optional[List[Entity]] = None
    crawl_date: Optional[str] = None
    snapshot_at: Optional[str] = None

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
        entities=None,
        crawl_date=None,
        snapshot_at=None,
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
        self.entities = entities
        self.crawl_date = crawl_date
        self.snapshot_at = snapshot_at

    def __str__(self):
        result = (
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
            f"Crawl Date: {self.crawl_date}\n"
            f"Snapshot At: {self.snapshot_at}\n"
        )
        if self.entities:
            entities_str = "\n".join(
                f"  - [{e.type}] {e.properties.name or 'Unknown'}"
                for e in self.entities
            )
            result += f"Entities:\n{entities_str}\n"
        return result


@dataclass
class Result(_Result):
    """
    A class representing a search result with optional text, summary, and highlights.

    Attributes:
        text (str, optional): The text content of the page.
        summary (str, optional): A summary of the page content.
        highlights (List[str], optional): Relevant sentences from the page.
        highlight_scores (List[float], optional): Scores for each highlight.
    """

    text: Optional[str] = None
    summary: Optional[str] = None
    highlights: Optional[List[str]] = None
    highlight_scores: Optional[List[float]] = None

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
        entities=None,
        crawl_date=None,
        snapshot_at=None,
        text=None,
        summary=None,
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
            entities,
            crawl_date,
            snapshot_at,
        )
        self.text = text
        self.summary = summary
        self.highlights = highlights
        self.highlight_scores = highlight_scores

    def __str__(self):
        base_str = super().__str__()
        result = base_str + f"Text: {self.text}\nSummary: {self.summary}\n"
        if self.highlights:
            result += f"Highlights: {self.highlights}\n"
        if self.highlight_scores:
            result += f"Highlight Scores: {self.highlight_scores}\n"
        return result


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
        entities=None,
        crawl_date=None,
        snapshot_at=None,
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
            entities,
            crawl_date,
            snapshot_at,
        )
        self.text = text

    def __str__(self):
        base_str = super().__str__()
        return base_str + f"Text: {self.text}\n"


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
        entities=None,
        crawl_date=None,
        snapshot_at=None,
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
            entities,
            crawl_date,
            snapshot_at,
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
        entities=None,
        crawl_date=None,
        snapshot_at=None,
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
            entities,
            crawl_date,
            snapshot_at,
        )
        self.text = text
        self.summary = summary

    def __str__(self):
        base_str = super().__str__()
        return base_str + f"Text: {self.text}\n" + f"Summary: {self.summary}\n"


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
        content (Optional[str]): The partial text content of the streamed response.
        citations (Optional[List[AnswerResult]]): List of citations if provided in this chunk.
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
class ApiWarning:
    """A warning the Exa API returns about a request, such as a field it ignores.

    A warning never changes the status code or the result. It is for whoever
    owns the code that builds the request: fix the request, and do not pass the
    warning to a model. Today /search returns them, in its response and stream.

    Attributes:
        code (str): Machine-readable code in UPPER_SNAKE case, such as
            'IGNORED_FIELD' (the field is accepted and has no effect). The set
            of codes is open, so handle codes you do not know.
        path (str): JSON Pointer to the request field the warning is about,
            such as '/startCrawlDate'.
        message (str): What to change in the request, in plain words.
    """

    code: str
    path: str
    message: str


SearchWarning = ApiWarning
"""A warning about a search request: an `ApiWarning`."""


def parse_api_warnings(raw: Any) -> Optional[List[ApiWarning]]:
    """Parse a response's `warnings` array.

    Args:
        raw: Raw `warnings` field from the API payload. The API omits the field
            when there are no warnings.

    Returns:
        The warnings, or None when the payload carries no `warnings` array.
        Items without a string `code`, `path` and `message` are skipped, so a
        malformed warning never fails a request.
    """

    if not isinstance(raw, list):
        return None

    return [
        ApiWarning(code=item["code"], path=item["path"], message=item["message"])
        for item in raw
        if isinstance(item, dict)
        and isinstance(item.get("code"), str)
        and isinstance(item.get("path"), str)
        and isinstance(item.get("message"), str)
    ]


parse_search_warnings = parse_api_warnings


@dataclass
class SearchNotice:
    """A note about how the results of a search were produced.

    For example, a query restriction relaxed to return results. A notice is
    written to be shown to a model. Pass its `message` to the model that reads
    the results.

    Attributes:
        code (str): Machine-readable code in UPPER_SNAKE case, such as
            'RESTRICTIONS_RELAXED' (no results matched a restriction in the
            query, so the results come from a search with it removed). The set
            of codes is open, so handle codes you do not know.
        path (str): JSON Pointer to the request field the notice is about,
            such as '/query'.
        message (str): Complete on its own and written to be shown to a model.
        details (Dict[str, Any], optional): Extra context, with keys as the API
            sent them. No schema is promised for its keys, and it never carries
            information that `message` lacks.
    """

    code: str
    path: str
    message: str
    details: Optional[Dict[str, Any]] = None


def parse_search_notices(raw: Any) -> Optional[List[SearchNotice]]:
    """Parse the `notices` array of a /search response.

    Args:
        raw: Raw `notices` field from the API payload. The API omits the field
            when there are no notices.

    Returns:
        The notices, or None when the payload carries no `notices` array.
        Items without a string `code`, `path` and `message` are skipped, so a
        malformed notice never fails a search. `details` is None unless it is
        an object.
    """

    if not isinstance(raw, list):
        return None

    return [
        SearchNotice(
            code=item["code"],
            path=item["path"],
            message=item["message"],
            details=item["details"] if isinstance(item.get("details"), dict) else None,
        )
        for item in raw
        if isinstance(item, dict)
        and isinstance(item.get("code"), str)
        and isinstance(item.get("path"), str)
        and isinstance(item.get("message"), str)
    ]


@dataclass
class SearchStreamChunk(StreamChunk):
    """A single chunk of a streaming search response.

    Attributes:
        content (Optional[str]): The partial text content of the streamed response.
        citations (Optional[List[AnswerResult]]): List of citations if provided in this chunk.
        warnings (Optional[List[ApiWarning]]): Notes about the request, such as
            a field the API ignores. When the API returns any, they arrive on one
            chunk of their own, after the streamed text.
    """

    warnings: Optional[List[ApiWarning]] = None

    def has_data(self) -> bool:
        """Check if this chunk contains any data."""
        return super().has_data() or bool(self.warnings)


@dataclass
class AnswerResponse:
    """A class representing the response for an answer operation.

    Attributes:
        answer (str): The generated answer.
        citations (List[AnswerResult]): A list of citations used to generate the answer.
        cost_dollars (CostDollars, optional): The cost breakdown for this request.
    """

    answer: Union[str, dict[str, Any]]
    citations: List[AnswerResult]
    cost_dollars: Optional[CostDollars] = None

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


def _stream_cost_dollars(payload: Any) -> Optional[CostDollars]:
    """The cost breakdown one stream event carries, or None for an event without one."""
    if not isinstance(payload, dict) or not isinstance(payload.get("costDollars"), dict):
        return None
    return parse_cost_dollars(payload["costDollars"])


class StreamAnswerResponse:
    """A streaming answer response.

    Iterating yields StreamChunk objects with partial text and citations.

    Attributes:
        cost_dollars (CostDollars, optional): The cost breakdown for this request.
            The API sends it at the end of the stream, so it is None until the
            stream has been read to the end.
    """

    cost_dollars: Optional[CostDollars]

    def __init__(self, raw_response: requests.Response):
        self._raw_response = raw_response
        self.cost_dollars = None
        self._ensure_ok_status()

    def _record_cost(self, payload: Any) -> None:
        """Keep the cost breakdown when this stream event carries one."""
        cost_dollars = _stream_cost_dollars(payload)
        if cost_dollars is not None:
            self.cost_dollars = cost_dollars

    def _ensure_ok_status(self):
        if self._raw_response.status_code != 200:
            raise ValueError(
                f"Request failed with status code {self._raw_response.status_code}: {self._raw_response.text}"
            )

    @typed_timeouts
    def __iter__(self) -> Iterator[StreamChunk]:
        for line in self._raw_response.iter_lines():
            if not line:
                continue
            decoded_line = line.decode("utf-8").removeprefix("data: ")
            try:
                chunk = json.loads(decoded_line)
            except json.JSONDecodeError:
                continue

            self._record_cost(chunk)
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

            stream_chunk = self._build_chunk(chunk, content, citations)
            if stream_chunk.has_data():
                yield stream_chunk

    def _build_chunk(
        self,
        payload: Dict[str, Any],
        content: Optional[str],
        citations: Optional[List[AnswerResult]],
    ) -> StreamChunk:
        """Build the chunk yielded for one stream payload."""
        return StreamChunk(content=content, citations=citations)

    def close(self) -> None:
        """Close the underlying raw response to release the network socket."""
        self._raw_response.close()


class AsyncStreamAnswerResponse:
    """A streaming answer response for the async client.

    Iterating with ``async for`` yields StreamChunk objects with partial text
    and citations.

    Attributes:
        cost_dollars (CostDollars, optional): The cost breakdown for this request.
            The API sends it at the end of the stream, so it is None until the
            stream has been read to the end.
    """

    cost_dollars: Optional[CostDollars]

    def __init__(self, raw_response: httpx.Response):
        self._raw_response = raw_response
        self.cost_dollars = None
        self._ensure_ok_status()

    def _record_cost(self, payload: Any) -> None:
        """Keep the cost breakdown when this stream event carries one."""
        cost_dollars = _stream_cost_dollars(payload)
        if cost_dollars is not None:
            self.cost_dollars = cost_dollars

    def _ensure_ok_status(self):
        if self._raw_response.status_code != 200:
            raise ValueError(
                f"Request failed with status code {self._raw_response.status_code}: {self._raw_response.text}"
            )

    def __aiter__(self):
        @typed_timeouts
        async def generator():
            try:
                async for line in self._raw_response.aiter_lines():
                    if not line:
                        continue
                    decoded_line = line.removeprefix("data: ")
                    try:
                        chunk = json.loads(decoded_line)
                    except json.JSONDecodeError:
                        continue

                    self._record_cost(chunk)
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

                    stream_chunk = self._build_chunk(chunk, content, citations)
                    if stream_chunk.has_data():
                        yield stream_chunk
            finally:
                await self._raw_response.aclose()

        return generator()

    def _build_chunk(
        self,
        payload: Dict[str, Any],
        content: Optional[str],
        citations: Optional[List[AnswerResult]],
    ) -> StreamChunk:
        """Build the chunk yielded for one stream payload."""
        return StreamChunk(content=content, citations=citations)

    async def aclose(self) -> None:
        """Close the async response to release the network socket."""
        await self._raw_response.aclose()

    def close(self) -> None:
        """Preserve the legacy method name with guidance for async callers."""
        raise RuntimeError("Use `await stream.aclose()` for asynchronous streams")


def _citations_from_results(results: Any) -> Optional[List[AnswerResult]]:
    """The ``results`` of a search response as stream citations.

    Each citation keeps the fields an `AnswerResult` has. Returns None when
    there are no results, so the chunk carrying them is left out.
    """
    if not isinstance(results, list):
        return None
    citations = [
        AnswerResult(
            id=result.get("id"),
            url=result.get("url"),
            title=result.get("title"),
            published_date=result.get("publishedDate"),
            author=result.get("author"),
            text=result.get("text"),
        )
        for result in results
        if isinstance(result, dict)
    ]
    return citations or None


def _search_json_chunks(payload: Any) -> List[SearchStreamChunk]:
    """The chunks for a search response the API sent whole as JSON instead of streaming it.

    The first carries the results as ``citations``, the second the request's
    ``warnings``. A chunk with nothing in it is left out, as in a stream.
    Issues no warnings: the caller reports them once for the whole response.
    """
    if not isinstance(payload, dict):
        return []
    chunks = [
        SearchStreamChunk(citations=_citations_from_results(payload.get("results"))),
        SearchStreamChunk(warnings=parse_search_warnings(payload.get("warnings"))),
    ]
    return [chunk for chunk in chunks if chunk.has_data()]


class StreamSearchResponse(StreamAnswerResponse):
    """A class representing a streaming search response.

    Iterating yields SearchStreamChunk objects with partial text and citations,
    and one chunk with the request's warnings when the API returns any.
    A search without ``output_schema`` has no text to stream. Its stream yields
    one chunk with the results as ``citations``, then the warnings chunk when
    the API returns warnings.

    Attributes:
        cost_dollars (CostDollars, optional): The cost breakdown for this request.
            It is None until the stream has been read to the end.
    """

    def __iter__(self) -> Iterator[SearchStreamChunk]:
        if _is_json_response(self._raw_response):
            return self._iter_json()
        return cast(Iterator[SearchStreamChunk], super().__iter__())

    @typed_timeouts
    def _iter_json(self) -> Iterator[SearchStreamChunk]:
        """Yield the chunks of a search response the API sent whole as JSON.

        Reports the response's warnings once, before the first chunk.

        Raises:
            ValueError: If the body is empty or not valid JSON.
        """
        try:
            payload = _decode_json_body(self._raw_response)
        finally:
            self._raw_response.close()
        self._record_cost(payload)
        issue_body_warnings(
            "/search", "POST", payload, self._raw_response.headers.get("x-request-id")
        )
        yield from _search_json_chunks(payload)

    def _build_chunk(
        self,
        payload: Dict[str, Any],
        content: Optional[str],
        citations: Optional[List[AnswerResult]],
    ) -> SearchStreamChunk:
        """Build the chunk yielded for one stream payload, with its warnings."""
        issue_body_warnings("/search", "POST", payload)
        return SearchStreamChunk(
            content=content,
            citations=citations,
            warnings=parse_search_warnings(payload.get("warnings")),
        )


class AsyncStreamSearchResponse(AsyncStreamAnswerResponse):
    """A class representing a streaming search response.

    Iterating yields SearchStreamChunk objects with partial text and citations,
    and one chunk with the request's warnings when the API returns any.
    A search without ``output_schema`` has no text to stream. Its stream yields
    one chunk with the results as ``citations``, then the warnings chunk when
    the API returns warnings.

    Attributes:
        cost_dollars (CostDollars, optional): The cost breakdown for this request.
            It is None until the stream has been read to the end.
    """

    def __aiter__(self) -> AsyncIterator[SearchStreamChunk]:
        if _is_json_response(self._raw_response):
            return self._aiter_json()
        return cast(AsyncIterator[SearchStreamChunk], super().__aiter__())

    @typed_timeouts
    async def _aiter_json(self) -> AsyncIterator[SearchStreamChunk]:
        """Yield the chunks of a search response the API sent whole as JSON.

        Reports the response's warnings once, before the first chunk.

        Raises:
            ValueError: If the body is empty or not valid JSON.
        """
        try:
            await self._raw_response.aread()
            payload = _decode_json_body(self._raw_response)
        finally:
            await self._raw_response.aclose()
        self._record_cost(payload)
        issue_body_warnings(
            "/search", "POST", payload, self._raw_response.headers.get("x-request-id")
        )
        for chunk in _search_json_chunks(payload):
            yield chunk

    def _build_chunk(
        self,
        payload: Dict[str, Any],
        content: Optional[str],
        citations: Optional[List[AnswerResult]],
    ) -> SearchStreamChunk:
        """Build the chunk yielded for one stream payload, with its warnings."""
        issue_body_warnings("/search", "POST", payload)
        return SearchStreamChunk(
            content=content,
            citations=citations,
            warnings=parse_search_warnings(payload.get("warnings")),
        )


T = TypeVar("T")


@dataclass
class ContentStatusError:
    """Error details for a URL whose content could not be retrieved.

    Attributes:
        tag (str, optional): Specific error type.
        http_status_code (int, optional): The corresponding HTTP status code.
    """

    tag: Optional[str] = None
    http_status_code: Optional[int] = None


@dataclass
class ContentStatus:
    """A class representing the status of a content retrieval operation.

    Attributes:
        id (str): The URL or document ID that was requested.
        status (str): Status of the content fetch operation.
        source (str, optional): Where the returned content was sourced from.
        error (ContentStatusError, optional): Error details, only present when status is "error".
    """

    id: str
    status: str
    source: Optional[str] = None
    error: Optional[ContentStatusError] = None


def _parse_content_status(raw: Dict[str, Any]) -> ContentStatus:
    """Build a ContentStatus from one entry of a contents response's `statuses`."""
    error = raw.get("error")
    return ContentStatus(
        id=raw.get("id"),
        status=raw.get("status"),
        source=raw.get("source"),
        error=ContentStatusError(
            tag=error.get("tag"),
            http_status_code=error.get("httpStatusCode"),
        )
        if isinstance(error, dict)
        else None,
    )


@dataclass
class SearchResponse(Generic[T]):
    """A class representing the response for a search operation.

    Attributes:
        results (List[Result]): A list of search results.
        resolved_search_type (str, optional): 'neural' or 'keyword' if auto.
        auto_date (str, optional): A date for filtering if autoprompt found one.
        context (str, optional): Deprecated. Combined context string. Use highlights, text, or output.
        output (DeepSearchOutput, optional): Search synthesized output object returned
            when output_schema is provided, containing content and field-level
            grounding.
        statuses (List[ContentStatus], optional): Status list from get_contents.
        cost_dollars (CostDollars, optional): Cost breakdown.
        search_time (float, optional): Time taken for the search in milliseconds.
        warnings (List[ApiWarning], optional): Notes about the search request,
            such as a field the API ignores. None when the API returned none.
        notices (List[SearchNotice], optional): Notes about how the results were
            produced, written to be shown to a model. None when the API
            returned none.
    """

    results: List[T]
    resolved_search_type: Optional[str]
    auto_date: Optional[str]
    context: Optional[str] = None  # DEPRECATED FIELD: legacy context response. Use highlights/text/output.
    output: Optional["DeepSearchOutput"] = None
    statuses: Optional[List[ContentStatus]] = None
    cost_dollars: Optional[CostDollars] = None
    search_time: Optional[float] = None
    warnings: Optional[List[ApiWarning]] = None
    notices: Optional[List[SearchNotice]] = None

    def __str__(self):
        output = "\n\n".join(str(result) for result in self.results)
        if self.context:  # DEPRECATED FIELD: legacy context response.
            output += f"\nContext: {self.context}"
        if self.output is not None:
            output += f"\nOutput: {self.output}"
        if self.resolved_search_type:
            output += f"\nResolved Search Type: {self.resolved_search_type}"
        if self.search_time is not None:
            output += f"\nSearch Time: {self.search_time}ms"
        if self.cost_dollars:
            output += f"\nCostDollars: total={self.cost_dollars.total}"
            if self.cost_dollars.search:
                output += f"\n  - search: {self.cost_dollars.search}"
            if self.cost_dollars.contents:
                output += f"\n  - contents: {self.cost_dollars.contents}"
        if self.statuses:
            output += f"\nStatuses: {self.statuses}"
        return output


@dataclass
class DeepSearchOutputGroundingCitation:
    """Citation metadata for one grounded output field."""

    url: str
    title: str


DeepSearchOutputGroundingConfidence = Literal["low", "medium", "high"]
"""Confidence levels for a grounded output field."""


@dataclass
class DeepSearchOutputGrounding:
    """Grounding metadata for one field in search synthesized output."""

    field: str
    citations: List[DeepSearchOutputGroundingCitation]
    confidence: DeepSearchOutputGroundingConfidence


@dataclass
class DeepSearchOutput:
    """Search synthesized output payload."""

    content: Union[str, dict[str, Any]]
    grounding: List[DeepSearchOutputGrounding]


def parse_deep_search_output(raw: Any) -> Optional[DeepSearchOutput]:
    """Parse search output into a typed object.

    Args:
        raw: Raw `output` field from API response.

    Returns:
        Parsed DeepSearchOutput when the payload is an object, otherwise None.
    """

    if not isinstance(raw, dict):
        return None

    raw_content = raw.get("content")
    if isinstance(raw_content, str):
        content: Union[str, dict[str, Any]] = raw_content
    elif isinstance(raw_content, dict):
        content = raw_content
    else:
        content = ""

    grounding: List[DeepSearchOutputGrounding] = []
    raw_grounding = raw.get("grounding")
    if isinstance(raw_grounding, list):
        for grounding_row in raw_grounding:
            if not isinstance(grounding_row, dict):
                continue

            field = grounding_row.get("field")
            if not isinstance(field, str):
                continue

            citations: List[DeepSearchOutputGroundingCitation] = []
            raw_citations = grounding_row.get("citations")
            if isinstance(raw_citations, list):
                for citation in raw_citations:
                    if not isinstance(citation, dict):
                        continue
                    url = citation.get("url")
                    title = citation.get("title")
                    if not isinstance(url, str):
                        continue
                    citations.append(
                        DeepSearchOutputGroundingCitation(
                            url=url,
                            title=title if isinstance(title, str) else "",
                        )
                    )

            confidence = grounding_row.get("confidence")
            if confidence not in ("low", "medium", "high"):
                confidence = "medium"

            grounding.append(
                DeepSearchOutputGrounding(
                    field=field,
                    citations=citations,
                    confidence=confidence,
                )
            )

    return DeepSearchOutput(content=content, grounding=grounding)


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


# A timeout bounds connecting and the wait for a response to start, never a
# stream that is flowing: once a successful streamed response's headers have
# arrived, its events may come as far apart as the server sends them. An error
# response is read whole, under the timeout, for the error message.


def _body_socket(raw: Any) -> Any:
    """Return the socket a urllib3 response reads its body from, or None.

    http.client reads the body through a file object made from the socket
    (``raw._fp.fp.raw._sock`` on urllib3 1.26 and 2.x). A response that ends
    the connection (``Connection: close``, HTTP/1.0) is handed the socket and
    the connection lets go of it, so the file object is the one way to reach
    it; ``raw.connection.sock`` is the same socket while the connection stays
    open.
    """
    body_file = getattr(getattr(raw, "_fp", None), "fp", None)
    sock = getattr(getattr(body_file, "raw", None), "_sock", None)
    if sock is None:
        sock = getattr(getattr(raw, "connection", None), "sock", None)
    return sock


def _started_stream(response: requests.Response) -> requests.Response:
    """Return a streamed Requests response with its body untimed, or raise for an error status.

    Requests applies the read timeout to the socket, which urllib3 then reads
    the body through, so the socket's timeout is cleared.

    Raises:
        ValueError: If the response has an error status.
    """
    if response.status_code >= 400:
        message = f"Request failed with status code {response.status_code}: {response.text}"
        response.close()
        raise ValueError(message)
    if 200 <= response.status_code < 300:
        sock = _body_socket(response.raw)
        if sock is not None:
            sock.settimeout(None)
    return response


async def _started_async_stream(response: httpx.Response) -> httpx.Response:
    """Return a streamed HTTPX response with its body untimed, or raise for an error status.

    HTTPX hands its request's ``timeout`` extension to the connection, which
    looks up the read timeout when the body starts to be read, so a read
    timeout of None set there now leaves the body untimed.

    Raises:
        ValueError: If the response has an error status.
    """
    if response.status_code >= 400:
        body = await response.aread()
        await response.aclose()
        error_text = body.decode(errors="replace")
        raise ValueError(
            f"Request failed with status code {response.status_code}: {error_text}"
        )
    if 200 <= response.status_code < 300:
        extensions = response.request.extensions
        extensions["timeout"] = {**extensions.get("timeout", {}), "read": None}
    return response


class Exa:
    """A client for interacting with Exa API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.exa.ai",
        user_agent: Optional[str] = None,
        timeout: Optional[float] = DEFAULT_REQUEST_TIMEOUT,
    ):
        """Initialize the Exa client with the provided API key and optional base URL and user agent.

        Args:
            api_key (str, optional): The API key for authenticating with the Exa API.
                Defaults to the EXA_API_KEY environment variable.
            base_url (str, optional): The base URL for the Exa API. Defaults to "https://api.exa.ai".
            user_agent (str, optional): Custom user agent. Defaults to "exa-py {version}".
            timeout (float, optional): Default timeout in seconds for API requests.
                Defaults to 600. Pass ``None`` to disable. Methods that accept
                ``timeout`` can override this per call.
        """
        if api_key is None:
            api_key = os.environ.get("EXA_API_KEY")
            if api_key is None:
                raise ValueError(
                    "API key must be provided as an argument or in EXA_API_KEY environment variable"
                )

        # Set default user agent with dynamic version if not provided
        if user_agent is None:
            user_agent = f"exa-py/{_get_package_version()}"

        self.base_url = base_url
        self.timeout = _validate_timeout(timeout)
        self.headers = {
            "x-api-key": api_key,
            "User-Agent": user_agent,
            "Content-Type": "application/json",
        }
        self.websets = WebsetsClient(self)
        # Research tasks client (new, mirrors Websets design)
        self.research = ResearchClient(self)
        # Search Monitors client
        self.monitors = SearchMonitorsClient(self)
        # Agent clients
        self.agent = AgentNamespace(self)
        self.beta = BetaClient(self)
        self._tool_registry = _ToolRegistry()
        self.tools = ToolNamespace(self, self._tool_registry)
        self.openai = OpenAINamespace(self, self._tool_registry)
        self.anthropic = AnthropicNamespace(self, self._tool_registry)

    @typed_timeouts
    def request(
        self,
        endpoint: str,
        data: Optional[Union[Dict[str, Any], str]] = None,
        method: str = "POST",
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        extra_headers: Optional[Mapping[str, Optional[str]]] = None,
        extra_query: Optional[Mapping[str, Any]] = None,
        extra_body: Optional[Mapping[str, Any]] = None,
    ) -> Union[Dict[str, Any], requests.Response]:
        """Send a request to the Exa API, optionally streaming if data['stream'] is True.

        Args:
            endpoint (str): The API endpoint (path).
            data (dict, optional): The JSON payload to send. Defaults to None.
            method (str, optional): The HTTP method to use. Defaults to "POST".
            params (Dict[str, Any], optional): Query parameters to include. Defaults to None.
            headers (Dict[str, str], optional): Additional headers to include in the request. Defaults to None.
            timeout (float, optional): Timeout in seconds for this request.
                Defaults to the client timeout. It bounds connecting and each wait
                for data from the server, not the whole call. For a streamed
                response it bounds the wait for the response to start. Once a
                successful response's headers have arrived, the stream is read
                with no timeout. An error response is read whole under it.
            extra_headers (Mapping[str, Optional[str]], optional): Extra headers. A header
                the client already sets is replaced, case-insensitively. Headers set to
                None are skipped. They do not change whether the response streams.
                ``data``, ``params`` and ``headers`` decide that. An
                ``Accept: text/event-stream`` set in ``headers``, as the Agent streams set
                it, stays. Any other ``Accept``, such as the default one the other streams
                send, is replaced.
            extra_query (Mapping[str, Any], optional): Extra query parameters, except
                ``stream``. Parameters set to None are skipped. On a GET request they
                are merged over ``params``.
            extra_body (Mapping[str, Any], optional): Extra fields merged over the JSON
                payload of a POST or PATCH request, except ``stream``.

        Returns:
            Union[dict, requests.Response]: If streaming, returns the Response object.
            Otherwise, returns the JSON-decoded response as a dict.

        Raises:
            ValueError: If the request fails (non-200 status code), or a successful
                response's body is not JSON.
            ExaTimeoutError: If connecting, waiting for the response to start, or
                waiting for more of a response that is not streamed exceeds the
                timeout. It is also an instance of the exception Requests raised. That
                is a requests.exceptions.Timeout subclass while connecting or waiting
                for the response to start, and requests.exceptions.ConnectionError when
                the response stalls after it started. A connect timeout is a
                requests.exceptions.ConnectTimeout, which is also a ConnectionError.
            TypeError: If ``extra_body`` is given with a pre-serialized string payload.
        """
        if method.upper() in ("POST", "PATCH"):
            data = merge_body(data, extra_body)
            warn_deprecated_fields(endpoint, data)
        # GET requests send `params` with the extra query merged over them; the
        # other methods send only the query string the call adds.
        extra_params = merge_query(None, extra_query)
        query_kwargs: Dict[str, Any] = {"params": extra_params} if extra_params else {}
        params = merge_query(params, extra_query)

        # Handle the case when data is a string
        if isinstance(data, str):
            # Use the string directly as the data payload
            json_data = data
        else:
            # Otherwise, serialize the dictionary to JSON if it exists
            json_data = json.dumps(data, cls=ExaJSONEncoder) if data else None

        # Check if we need streaming (either from data for POST or params for GET)
        # Merge additional headers with existing headers
        request_headers = {**self.headers}
        if headers:
            request_headers.update(headers)

        # Check if we need streaming (either from data, params, or SSE Accept header).
        # Decided before the extra headers are applied: they change what is sent,
        # not how the response is read. merge_body and merge_query never take
        # `stream` from the extras for the same reason.
        needs_streaming = (
            (data and isinstance(data, dict) and data.get("stream"))
            or (params and params.get("stream") == "true")
            or request_headers.get("Accept") == "text/event-stream"
        )
        request_headers = merge_headers(request_headers, extra_headers)

        request_timeout = _validate_timeout(timeout) if timeout is not None else self.timeout

        with reporting_failover_connect_timeouts(request_timeout):
            if method.upper() == "GET":
                if needs_streaming:
                    res = requests.get(
                        self.base_url + endpoint,
                        headers=request_headers,
                        params=params,
                        stream=True,
                        timeout=request_timeout,
                    )
                    return _started_stream(res)
                else:
                    res = requests.get(
                        self.base_url + endpoint,
                        headers=request_headers,
                        params=params,
                        timeout=request_timeout,
                    )
            elif method.upper() == "POST":
                if needs_streaming:
                    res = requests.post(
                        self.base_url + endpoint,
                        data=json_data,
                        headers=request_headers,
                        stream=True,
                        timeout=request_timeout,
                        **query_kwargs,
                    )
                    return _started_stream(res)
                else:
                    res = requests.post(
                        self.base_url + endpoint,
                        data=json_data,
                        headers=request_headers,
                        timeout=request_timeout,
                        **query_kwargs,
                    )
            elif method.upper() == "PATCH":
                res = requests.patch(
                    self.base_url + endpoint,
                    data=json_data,
                    headers=request_headers,
                    timeout=request_timeout,
                    **query_kwargs,
                )
            elif method.upper() == "DELETE":
                res = requests.delete(
                    self.base_url + endpoint,
                    headers=request_headers,
                    timeout=request_timeout,
                    **query_kwargs,
                )
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

        if res.status_code >= 400:
            raise ValueError(
                f"Request failed with status code {res.status_code}: {res.text}"
            )
        payload = _decode_json_body(res)
        issue_body_warnings(endpoint, method, payload, res.headers.get("x-request-id"))
        return payload

    def search(
        self,
        query: str,
        *,
        stream: Optional[bool] = False,
        contents: Optional[Union[ContentsOptions, Literal[False]]] = None,
        num_results: Optional[int] = None,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        start_crawl_date: Optional[str] = None,
        end_crawl_date: Optional[str] = None,
        start_published_date: Optional[str] = None,
        end_published_date: Optional[str] = None,
        include_text: Optional[List[str]] = None,
        exclude_text: Optional[List[str]] = None,
        type: Optional[Union[SearchType, str]] = None,
        category: Optional[Category] = None,
        flags: Optional[List[str]] = None,
        moderation: Optional[bool] = None,
        user_location: Optional[Union[str, UserLocation]] = None,
        additional_queries: Optional[List[str]] = None,
        system_prompt: Optional[str] = None,
        output_schema: Optional[DeepOutputSchema] = None,
        objective: Optional[str] = None,
        user_identifier: Optional[str] = None,
        betas: Optional[Sequence[str]] = None,
        extra_body: Optional[Mapping[str, Any]] = None,
        timeout: Optional[float] = None,
        extra_headers: Optional[Mapping[str, Optional[str]]] = None,
        extra_query: Optional[Mapping[str, Any]] = None,

    ) -> SearchResponse[Result]:
        """Perform a search.

        For AI answers, RAG, and search previews, use ``contents={"highlights": True}``
        and read each result's ``highlights`` list. Exa dynamically chooses the
        number of characters based on each document's relevance to your query.
        No manual character budget is needed. Set ``max_characters`` only when
        your application requires a specific numeric character limit; otherwise
        keep ``highlights=True``. Do not use the deprecated ``num_sentences`` or
        ``highlights_per_url`` options.

        Request text when you need full-page content, or use contents=False for
        titles and URLs only. Omitting contents still returns text with 10,000
        max characters by default.

        Args:
            extra_body (Optional[Mapping[str, Any]]): Per-call body overrides, except stream.
            query (str): The query string.
            stream (bool, optional): If True, stream the synthesized search response.
                Use ``stream_search(...)`` instead of ``search(..., stream=True)``.
            contents (ContentsOptions | False, optional): Options for retrieving page contents.
                Defaults to {"text": {"maxCharacters": 10000}}. Use False to disable contents.
                For AI context, prefer {"highlights": True} for relevance-based sizing
                and read result.highlights. See ContentsOptions for all options.
            num_results (int, optional): Number of search results to return. Default 10.
            include_domains (List[str], optional): Domains to include in the search.
            exclude_domains (List[str], optional): Domains to exclude from the search.
            start_crawl_date (str, optional): Deprecated and will be removed in a future release. Only links crawled after this date.
            end_crawl_date (str, optional): Deprecated and will be removed in a future release. Only links crawled before this date.
            start_published_date (str, optional): Only links published after this date.
            end_published_date (str, optional): Only links published before this date.
            include_text (List[str], optional): Strings that must appear in the page text.
            exclude_text (List[str], optional): Strings that must not appear in the page text.
            type (SearchType, optional): Search type - 'auto' (default), 'fast',
                'deep-lite', 'deep', 'deep-reasoning', 'neural', 'instant', or 'lite'
                (beta: low-cost, reduced parameter set).
            category (Category, optional): Data category to focus on (e.g.
                'company', 'news', 'publication').
            flags (List[str], optional): Experimental flags for Exa usage.
            moderation (bool, optional): If True, the search results will be moderated for safety.
            user_location (str | UserLocation, optional): The end user's location, as a
                two-letter ISO 3166-1 country code or a UserLocation dict.
            additional_queries (List[str], optional): Alternative query formulations for deep search to skip
                automatic LLM-based query expansion. Max 5 queries. Only applicable when type is
                'deep-lite', 'deep', or 'deep-reasoning'.
                Example: ["machine learning", "ML algorithms", "neural networks"]
            system_prompt (str, optional): Instructions that guide both the search process and
                the final returned result. Use this to prefer certain sources, emphasize novelty,
                avoid duplicates, or constrain the response style. Supported for all search types.
            output_schema (DeepOutputSchema, optional): Search output schema for structured
                synthesis. When provided, the API returns synthesized output in ``output``.
                Use ``{"type": "text", "description": ...}`` for plain text output or
                ``{"type": "object", "properties": ..., "required": ...}`` for structured JSON.
                For object schemas, max nesting depth is 2 and max total properties is 10.
                Supported for all search types.
            objective (str, optional): The broader goal this search serves: the task the
                caller is working on, beyond the query itself. When an agent picks the query
                as one step of a larger task, pass the goal of that step: which documents
                should rank first, which should be excluded, and what to pull from them.
                Up to 4096 characters.
            user_identifier (str, optional): An opaque ID you assign to the end user
                this request is made for, such as a UUID, used to attribute usage to
                that end user. Must not contain personal information such as an email
                address, phone number, username or name. Hash such values before
                sending them. 1 to 64 characters: letters, digits, ``_`` and ``-``.
                Retained even when your team has Zero Data Retention enabled. Does not
                affect results.
            betas (Sequence[str], optional): Exa-Beta tokens to send with the request
                (e.g. ``[DYNAMIC_HIGHLIGHTS_BETA]`` for Dynamic Highlights).
            timeout (float, optional): Per-operation network inactivity timeout in seconds. Defaults to the client timeout.
            extra_headers (Mapping[str, Optional[str]], optional): Extra headers to send with the request.
            extra_query (Mapping[str, Any], optional): Extra query parameters to send with the request.

        Returns:
            SearchResponse: The response containing search results, etc.

        Raises:
            ValueError: If stream=True is provided. Use stream_search() instead.

        Examples:
            # Query-relevant passages for AI context
            result = exa.search(
              "hottest AI startups",
              num_results=2,
              contents={"highlights": True}
            )
            for source in result.results:
                print(source.url, source.highlights)

            # Deep search with query variations
            deep_result = exa.search(
              "blog post about AI",
              type="deep",
              additional_queries=["AI blogpost", "machine learning blogs"],
              num_results=5
            )
        """
        if stream:
            raise ValueError(
                "stream=True is not supported in `search()`. "
                "Please use `stream_search(...)` for streaming."
            )

        options = {
            k: v
            for k, v in locals().items()
            if k not in _NON_BODY_ARGUMENTS and v is not None

        }
        options.pop("stream", None)
        options.pop("betas", None)

        # Handle contents parameter with default behavior
        if contents is False:
            # Explicitly no contents - remove from options
            options.pop("contents", None)
        elif contents is None and "contents" not in options:
            # No contents specified - add default text with 10,000 max characters
            options["contents"] = {"text": {"max_characters": DEFAULT_MAX_CHARACTERS}}
        elif contents is not None:
            # User provided contents - use as-is
            options["contents"] = contents

        _convert_contents_summary_schema(options)
        validate_search_options(options, SEARCH_OPTIONS_TYPES)
        options = to_camel_case(options, skip_keys=["output_schema", "schema"])
        options = _merge_search_body(options, extra_body)
        data = self.request(
            "/search",
            options,
            headers=headers_for_betas(betas),
            timeout=timeout,
            extra_headers=extra_headers,
            extra_query=extra_query,
        )

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
                    crawl_date=snake_result.get("crawl_date"),
                    snapshot_at=snake_result.get("snapshot_at"),
                    text=snake_result.get("text"),
                    summary=snake_result.get("summary"),
                    highlights=snake_result.get("highlights"),
                    highlight_scores=snake_result.get("highlight_scores"),
                    entities=_parse_entities(result.get("entities")),
                )
            )
        return SearchResponse(
            results,
            data["resolvedSearchType"] if "resolvedSearchType" in data else None,
            data["autoDate"] if "autoDate" in data else None,
            context=data.get("context"),  # DEPRECATED FIELD: legacy context response.
            output=parse_deep_search_output(data.get("output")),
            cost_dollars=cost_dollars,
            search_time=data.get("searchTime"),
            warnings=parse_search_warnings(data.get("warnings")),
            notices=parse_search_notices(data.get("notices")),
        )

    def stream_search(
        self,
        query: str,
        *,
        contents: Optional[Union[ContentsOptions, Literal[False]]] = None,
        num_results: Optional[int] = None,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        start_crawl_date: Optional[str] = None,
        end_crawl_date: Optional[str] = None,
        start_published_date: Optional[str] = None,
        end_published_date: Optional[str] = None,
        include_text: Optional[List[str]] = None,
        exclude_text: Optional[List[str]] = None,
        type: Optional[Union[SearchType, str]] = None,
        category: Optional[Category] = None,
        flags: Optional[List[str]] = None,
        moderation: Optional[bool] = None,
        user_location: Optional[Union[str, UserLocation]] = None,
        additional_queries: Optional[List[str]] = None,
        system_prompt: Optional[str] = None,
        output_schema: Optional[DeepOutputSchema] = None,
        objective: Optional[str] = None,
        user_identifier: Optional[str] = None,
        extra_body: Optional[Mapping[str, Any]] = None,
        timeout: Optional[float] = None,
        extra_headers: Optional[Mapping[str, Optional[str]]] = None,
        extra_query: Optional[Mapping[str, Any]] = None,

    ) -> StreamSearchResponse:
        """Generate a streaming search response.

        Args:
            extra_body (Optional[Mapping[str, Any]]): Per-call body overrides, except stream.
            query (str): The query string.
            contents (ContentsOptions | False, optional): Options for retrieving page contents.
                Defaults to {"text": {"maxCharacters": 10000}}. Use False to disable contents.
            num_results (int, optional): Number of search results to return. Default 10.
            include_domains (List[str], optional): Domains to include in the search.
            exclude_domains (List[str], optional): Domains to exclude from the search.
            start_crawl_date (str, optional): Deprecated and will be removed in a future release. Only links crawled after this date.
            end_crawl_date (str, optional): Deprecated and will be removed in a future release. Only links crawled before this date.
            start_published_date (str, optional): Only links published after this date.
            end_published_date (str, optional): Only links published before this date.
            include_text (List[str], optional): Strings that must appear in the page text.
            exclude_text (List[str], optional): Strings that must not appear in the page text.
            type (SearchType, optional): Search type - 'auto' (default), 'fast',
                'deep-lite', 'deep', 'deep-reasoning', 'neural', or 'instant'.
            category (Category, optional): Data category to focus on.
            flags (List[str], optional): Experimental flags for Exa usage.
            moderation (bool, optional): If True, the search results will be moderated for safety.
            user_location (str | UserLocation, optional): The end user's location, as a
                two-letter ISO 3166-1 country code or a UserLocation dict.
            additional_queries (List[str], optional): Alternative query formulations for deep search.
            system_prompt (str, optional): Instructions that guide the search process and streamed synthesis.
            output_schema (DeepOutputSchema, optional): Search output schema for structured synthesis.
            objective (str, optional): The broader goal this search serves: the task the
                caller is working on, beyond the query itself. Up to 4096 characters.
            user_identifier (str, optional): An opaque ID you assign to the end user
                this request is made for, such as a UUID, used to attribute usage to
                that end user. Must not contain personal information such as an email
                address, phone number, username or name. Hash such values before
                sending them. 1 to 64 characters: letters, digits, ``_`` and ``-``.
                Retained even when your team has Zero Data Retention enabled. Does not
                affect results.
            timeout (float, optional): Timeout in seconds for this request. Defaults to the client-level timeout.
                It bounds the wait for the stream to start. A stream that has started is not timed.
            extra_headers (Mapping[str, Optional[str]], optional): Extra headers to send with the request.
            extra_query (Mapping[str, Any], optional): Extra query parameters to send with the request.


        Returns:
            StreamSearchResponse: An iterator yielding OpenAI-style streaming chunks with
                partial ``content`` and optional ``citations``. When the API returns
                ``warnings`` about the request, one chunk after the text carries them.
                A search without ``output_schema`` has no text to stream. Its stream
                yields one chunk with the results as ``citations``, then the warnings
                chunk when the API returns warnings. Call ``search()`` for every field
                of the results. Once the stream has been read to the end, its
                ``cost_dollars`` holds the cost breakdown for this request.

        Examples:
            stream = exa.stream_search(
                "What are the latest battery breakthroughs?",
                type="auto",
                output_schema={"type": "text"},
            )

            for chunk in stream:
                if chunk.content:
                    print(chunk.content, end="", flush=True)
        """
        options = {
            k: v
            for k, v in locals().items()
            if k not in _NON_BODY_ARGUMENTS and v is not None

        }

        if contents is False:
            options.pop("contents", None)
        elif contents is None and "contents" not in options:
            options["contents"] = {"text": {"max_characters": DEFAULT_MAX_CHARACTERS}}
        elif contents is not None:
            options["contents"] = contents

        validate_search_options(options, SEARCH_OPTIONS_TYPES)
        options = to_camel_case(options, skip_keys=["output_schema"])
        options = _merge_search_body(options, extra_body, streaming=True)
        raw_response = self.request(
            "/search",
            options,
            timeout=timeout,
            extra_headers=extra_headers,
            extra_query=extra_query,
        )

        return StreamSearchResponse(raw_response)

    @deprecated(
        "search_and_contents() is deprecated. Use search() instead; "
        "search() returns text contents by default."
    )
    def search_and_contents(
        self,
        query: str,
        *,
        extra_body: Optional[Mapping[str, Any]] = None,
        extra_headers: Optional[Mapping[str, Optional[str]]] = None,
        extra_query: Optional[Mapping[str, Any]] = None,
        **kwargs: Any,
    ) -> SearchResponse[Result]:
        """
        DEPRECATED: Use search() instead. The search() method now returns text contents by default.

        Args:
            extra_body (Optional[Mapping[str, Any]]): Per-call body overrides, except stream.
            extra_headers (Mapping[str, Optional[str]], optional): Extra headers to send with the request.
            extra_query (Mapping[str, Any], optional): Extra query parameters to send with the request.

        Migration:
        - search_and_contents(query) → search(query)
        - search_and_contents(query, text=True) → search(query, contents={"text": True})
        - search_and_contents(query, summary=True) → search(query, contents={"summary": True})
        """

        timeout = kwargs.pop("timeout", None)
        options = {"query": query}
        for k, v in kwargs.items():
            if v is not None:
                options[k] = v
        # If user didn't ask for any particular content, default to text with max characters
        if (
            "text" not in options
            and "summary" not in options
            and "extras" not in options
        ):
            options["text"] = {"max_characters": DEFAULT_MAX_CHARACTERS}

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
        options = nest_fields(options, NESTED_CONTENTS_FIELDS, "contents")
        options = to_camel_case(options, skip_keys=["schema"])
        options = _merge_search_body(options, extra_body)
        data = self.request(
            "/search",
            options,
            timeout=timeout,
            extra_headers=extra_headers,
            extra_query=extra_query,
        )

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
                    crawl_date=snake_result.get("crawl_date"),
                    snapshot_at=snake_result.get("snapshot_at"),
                    text=snake_result.get("text"),
                    summary=snake_result.get("summary"),
                    highlights=snake_result.get("highlights"),
                    highlight_scores=snake_result.get("highlight_scores"),
                    entities=_parse_entities(result.get("entities")),
                )
            )
        return SearchResponse(
            results,
            data.get("resolvedSearchType"),
            data.get("autoDate"),
            context=data.get("context"),  # DEPRECATED FIELD: legacy context response.
            output=parse_deep_search_output(data.get("output")),
            cost_dollars=cost_dollars,
            search_time=data.get("searchTime"),
            warnings=parse_search_warnings(data.get("warnings")),
            notices=parse_search_notices(data.get("notices")),
        )

    @overload
    def get_contents(
        self,
        urls: Union[str, List[str], List[_Result]],
        *,
        livecrawl_timeout: Optional[int] = None,
        livecrawl: Optional[LIVECRAWL_OPTIONS] = None,
        max_age_hours: Optional[int] = None,
        snapshot_as_of: Optional[str] = None,
        filter_empty_results: Optional[bool] = None,
        subpages: Optional[int] = None,
        subpage_target: Optional[Union[str, List[str]]] = None,
        extras: Optional[ExtrasOptions] = None,
        flags: Optional[List[str]] = None,
        user_identifier: Optional[str] = None,
        betas: Optional[Sequence[str]] = None,
        timeout: Optional[float] = None,
        extra_headers: Optional[Mapping[str, Optional[str]]] = None,
        extra_query: Optional[Mapping[str, Any]] = None,
        extra_body: Optional[Mapping[str, Any]] = None,
    ) -> SearchResponse[ResultWithText]: ...

    @overload
    def get_contents(
        self,
        urls: Union[str, List[str], List[_Result]],
        *,
        text: Union[TextContentsOptions, Literal[True]],
        livecrawl_timeout: Optional[int] = None,
        livecrawl: Optional[LIVECRAWL_OPTIONS] = None,
        max_age_hours: Optional[int] = None,
        snapshot_as_of: Optional[str] = None,
        filter_empty_results: Optional[bool] = None,
        subpages: Optional[int] = None,
        subpage_target: Optional[Union[str, List[str]]] = None,
        extras: Optional[ExtrasOptions] = None,
        flags: Optional[List[str]] = None,
        user_identifier: Optional[str] = None,
        betas: Optional[Sequence[str]] = None,
        timeout: Optional[float] = None,
        extra_headers: Optional[Mapping[str, Optional[str]]] = None,
        extra_query: Optional[Mapping[str, Any]] = None,
        extra_body: Optional[Mapping[str, Any]] = None,
    ) -> SearchResponse[ResultWithText]: ...

    @overload
    def get_contents(
        self,
        urls: Union[str, List[str], List[_Result]],
        *,
        summary: Union[SummaryContentsOptions, Literal[True]],
        livecrawl_timeout: Optional[int] = None,
        livecrawl: Optional[LIVECRAWL_OPTIONS] = None,
        max_age_hours: Optional[int] = None,
        snapshot_as_of: Optional[str] = None,
        filter_empty_results: Optional[bool] = None,
        subpages: Optional[int] = None,
        subpage_target: Optional[Union[str, List[str]]] = None,
        extras: Optional[ExtrasOptions] = None,
        flags: Optional[List[str]] = None,
        user_identifier: Optional[str] = None,
        betas: Optional[Sequence[str]] = None,
        timeout: Optional[float] = None,
        extra_headers: Optional[Mapping[str, Optional[str]]] = None,
        extra_query: Optional[Mapping[str, Any]] = None,
        extra_body: Optional[Mapping[str, Any]] = None,
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
        max_age_hours: Optional[int] = None,
        snapshot_as_of: Optional[str] = None,
        filter_empty_results: Optional[bool] = None,
        subpages: Optional[int] = None,
        subpage_target: Optional[Union[str, List[str]]] = None,
        extras: Optional[ExtrasOptions] = None,
        flags: Optional[List[str]] = None,
        user_identifier: Optional[str] = None,
        betas: Optional[Sequence[str]] = None,
        timeout: Optional[float] = None,
        extra_headers: Optional[Mapping[str, Optional[str]]] = None,
        extra_query: Optional[Mapping[str, Any]] = None,
        extra_body: Optional[Mapping[str, Any]] = None,
    ) -> SearchResponse[ResultWithTextAndSummary]: ...

    # Every content option the method accepts, for the calls the overloads above
    # do not cover (highlights, metadata, context, or False for text or
    # summary). The result type is not narrowed for them.
    @overload
    def get_contents(
        self,
        urls: Union[str, List[str], List[_Result]],
        *,
        text: Optional[Union[TextContentsOptions, bool]] = None,
        summary: Optional[Union[SummaryContentsOptions, bool]] = None,
        highlights: Optional[Union[HighlightsContentsOptions, bool]] = None,
        metadata: Optional[Union[Dict[str, Any], bool]] = None,
        context: Optional[Union[ContextContentsOptions, bool]] = None,
        livecrawl_timeout: Optional[int] = None,
        livecrawl: Optional[LIVECRAWL_OPTIONS] = None,
        max_age_hours: Optional[int] = None,
        snapshot_as_of: Optional[str] = None,
        filter_empty_results: Optional[bool] = None,
        subpages: Optional[int] = None,
        subpage_target: Optional[Union[str, List[str]]] = None,
        extras: Optional[ExtrasOptions] = None,
        flags: Optional[List[str]] = None,
        user_identifier: Optional[str] = None,
        betas: Optional[Sequence[str]] = None,
        timeout: Optional[float] = None,
        extra_headers: Optional[Mapping[str, Optional[str]]] = None,
        extra_query: Optional[Mapping[str, Any]] = None,
        extra_body: Optional[Mapping[str, Any]] = None,
    ) -> SearchResponse[Any]: ...

    def get_contents(self, urls: Union[str, List[str], List[_Result]], **kwargs):
        """Retrieve contents for a list of URLs.

        Args:
            urls (str | List[str] | List[Result]): A single URL, list of URLs, or list of Result objects.
            text (TextContentsOptions | True, optional): Options for text extraction.
            summary (SummaryContentsOptions | True, optional): Options for summary generation.
            max_age_hours (int, optional): Maximum age of cached content in hours. If content is older,
                it will be fetched fresh. Special values: 0 = always fetch fresh content,
                -1 = never fetch fresh (cache only). Example: 168 = fetch fresh for pages older than 7 days.
            livecrawl (str, optional): Deprecated. Use ``max_age_hours`` instead. Does not guarantee
                freshly fetched content. Cannot be combined with ``max_age_hours``.
            snapshot_as_of (str, optional): ISO 8601 datetime. Return the newest stored version at or before this instant instead of live content.
            filter_empty_results (bool, optional): Whether to filter out empty results.
            subpages (int, optional): Number of subpages to retrieve.
            subpage_target (str | List[str], optional): Target subpages to retrieve.
            extras (ExtrasOptions, optional): Options for extra content (links, image_links).
            flags (List[str], optional): Experimental flags.
            user_identifier (str, optional): An opaque ID you assign to the end user
                this request is made for, such as a UUID, used to attribute usage to
                that end user. Must not contain personal information such as an email
                address, phone number, username or name. Hash such values before
                sending them. 1 to 64 characters: letters, digits, ``_`` and ``-``.
                Retained even when your team has Zero Data Retention enabled. Does not
                affect results.
            betas (Sequence[str], optional): Exa-Beta tokens to send with the request
                (e.g. ``[DYNAMIC_HIGHLIGHTS_BETA]`` for Dynamic Highlights).
            timeout (float, optional): Per-operation network inactivity timeout in seconds. Defaults to the client timeout.
            extra_headers (Mapping[str, Optional[str]], optional): Extra headers to send with the request.
            extra_query (Mapping[str, Any], optional): Extra query parameters to send with the request.
            extra_body (Mapping[str, Any], optional): Extra fields merged over the JSON request body, except stream.

        Returns:
            SearchResponse[Result]: The response containing the contents of the URLs.

        Examples:
            # Get contents for a single URL
            contents = exa.get_contents("https://example.com/article")

            # Get contents for multiple URLs
            contents = exa.get_contents([
                "https://example.com/article1",
                "https://example.com/article2"
            ])
        """
        # Normalize urls to always be a list
        if isinstance(urls, str):
            urls = [urls]
        elif isinstance(urls, list) and len(urls) > 0 and isinstance(urls[0], _Result):
            # Extract URLs from Result objects
            urls = [r.url for r in urls]

        betas = kwargs.pop("betas", None)
        timeout = kwargs.pop("timeout", None)
        extra_headers = kwargs.pop("extra_headers", None)
        extra_query = kwargs.pop("extra_query", None)
        extra_body = kwargs.pop("extra_body", None)

        options = {"urls": urls}
        for k, v in kwargs.items():
            if k != "self" and v is not None:
                options[k] = v

        if (
            "text" not in options
            and "summary" not in options
            and "extras" not in options
        ):
            options["text"] = {"max_characters": DEFAULT_MAX_CHARACTERS}

        merged_options = {}
        merged_options.update(CONTENTS_OPTIONS_TYPES)
        merged_options.update(CONTENTS_ENDPOINT_OPTIONS_TYPES)
        merged_options.update(CONTENTS_REQUEST_OPTIONS_TYPES)
        validate_search_options(options, merged_options)

        # Convert schema if present in summary options
        if "summary" in options and isinstance(options["summary"], dict):
            summary_opts = options["summary"]
            if "schema" in summary_opts:
                summary_opts["schema"] = _convert_schema_input(summary_opts["schema"])

        options = to_camel_case(options, ["schema"])
        data = self.request(
            "/contents",
            options,
            headers=headers_for_betas(betas),
            timeout=timeout,
            extra_headers=extra_headers,
            extra_query=extra_query,
            extra_body=extra_body,
        )
        cost_dollars = parse_cost_dollars(data.get("costDollars"))
        statuses = [_parse_content_status(status) for status in data.get("statuses", [])]
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
                    crawl_date=snake_result.get("crawl_date"),
                    snapshot_at=snake_result.get("snapshot_at"),
                    text=snake_result.get("text"),
                    summary=snake_result.get("summary"),
                    highlights=snake_result.get("highlights"),
                    highlight_scores=snake_result.get("highlight_scores"),
                    entities=_parse_entities(result.get("entities")),
                )
            )
        return SearchResponse(
            results,
            data.get("resolvedSearchType"),
            data.get("autoDate"),
            context=data.get("context"),  # DEPRECATED FIELD: legacy context response.
            cost_dollars=cost_dollars,
            statuses=statuses,
            search_time=data.get("searchTime"),
        )

    @deprecated("find_similar()/findSimilar is deprecated. Use search() instead.")
    def find_similar(
        self,
        url: str,
        *,
        contents: Optional[Union[ContentsOptions, Literal[False]]] = None,
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
        category: Optional[Category] = None,
        flags: Optional[List[str]] = None,
        timeout: Optional[float] = None,
        extra_headers: Optional[Mapping[str, Optional[str]]] = None,
        extra_query: Optional[Mapping[str, Any]] = None,
        extra_body: Optional[Mapping[str, Any]] = None,
    ) -> SearchResponse[Result]:
        """DEPRECATED METHOD: find_similar()/findSimilar is deprecated. Use search() instead.

        Migration:
            Use search("pages similar to " + url) instead of find_similar(url).

        Finds similar pages to a given URL, potentially with domain filters and date filters.

        By default, returns text contents with 10,000 max characters. Use contents=False to opt-out.

        Args:
            url (str): The URL to find similar pages for.
            contents (ContentsOptions | False, optional): Options for retrieving page contents.
                Defaults to {"text": {"maxCharacters": 10000}}. Use False to disable contents.
                See ContentsOptions for available options (text, highlights, summary, etc.).
            num_results (int, optional): Number of results to return. Default is None (server default).
            include_domains (List[str], optional): Domains to include in the search.
            exclude_domains (List[str], optional): Domains to exclude from the search.
            start_crawl_date (str, optional): Deprecated and will be removed in a future release. Only links crawled after this date.
            end_crawl_date (str, optional): Deprecated and will be removed in a future release. Only links crawled before this date.
            start_published_date (str, optional): Only links published after this date.
            end_published_date (str, optional): Only links published before this date.
            include_text (List[str], optional): Strings that must appear in the page text.
            exclude_text (List[str], optional): Strings that must not appear in the page text.
            exclude_source_domain (bool, optional): Whether to exclude the source domain.
            category (Category, optional): Data category to focus on (e.g.
                'company', 'news', 'publication').
            flags (List[str], optional): Experimental flags.
            timeout (float, optional): Timeout in seconds for this request. Defaults to the client-level timeout.
            extra_headers (Mapping[str, Optional[str]], optional): Extra headers to send with the request.
            extra_query (Mapping[str, Any], optional): Extra query parameters to send with the request.
            extra_body (Mapping[str, Any], optional): Extra fields merged over the JSON request body, except stream.

        Returns:
            SearchResponse[Result]

        Examples:
            url = "https://www.miniclip.com/games/en/"
            similar_results = exa.search(
                f"pages similar to {url}",
                num_results=2,
            )
        """
        options = {
            k: v
            for k, v in locals().items()
            if k not in _NON_BODY_ARGUMENTS and v is not None
        }

        # Handle contents parameter with default behavior
        if contents is False:
            # Explicitly no contents - remove from options
            options.pop("contents", None)
        elif contents is None and "contents" not in options:
            # No contents specified - add default text with 10,000 max characters
            options["contents"] = {"text": {"max_characters": DEFAULT_MAX_CHARACTERS}}
        elif contents is not None:
            # User provided contents - use as-is
            options["contents"] = contents

        validate_search_options(options, FIND_SIMILAR_OPTIONS_TYPES)
        options = to_camel_case(options)
        data = self.request(
            "/findSimilar",
            options,
            timeout=timeout,
            extra_headers=extra_headers,
            extra_query=extra_query,
            extra_body=extra_body,
        )
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
                    crawl_date=snake_result.get("crawl_date"),
                    snapshot_at=snake_result.get("snapshot_at"),
                    text=snake_result.get("text"),
                    summary=snake_result.get("summary"),
                    highlights=snake_result.get("highlights"),
                    highlight_scores=snake_result.get("highlight_scores"),
                    entities=_parse_entities(result.get("entities")),
                )
            )
        return SearchResponse(
            results,
            data.get("resolvedSearchType"),
            data.get("autoDate"),
            cost_dollars=cost_dollars,
            search_time=data.get("searchTime"),
        )

    @overload
    @deprecated(
        "find_similar_and_contents() is deprecated. Use search() instead; "
        "search() returns text contents by default."
    )
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
        category: Optional[Category] = None,
        flags: Optional[List[str]] = None,
        livecrawl_timeout: Optional[int] = None,
        livecrawl: Optional[LIVECRAWL_OPTIONS] = None,
        max_age_hours: Optional[int] = None,
        snapshot_as_of: Optional[str] = None,
        filter_empty_results: Optional[bool] = None,
        subpages: Optional[int] = None,
        subpage_target: Optional[Union[str, List[str]]] = None,
        extras: Optional[ExtrasOptions] = None,
        timeout: Optional[float] = None,
        extra_headers: Optional[Mapping[str, Optional[str]]] = None,
        extra_query: Optional[Mapping[str, Any]] = None,
        extra_body: Optional[Mapping[str, Any]] = None,
    ) -> SearchResponse[ResultWithText]: ...

    @overload
    @deprecated(
        "find_similar_and_contents() is deprecated. Use search() instead; "
        "search() returns text contents by default."
    )
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
        category: Optional[Category] = None,
        flags: Optional[List[str]] = None,
        livecrawl_timeout: Optional[int] = None,
        livecrawl: Optional[LIVECRAWL_OPTIONS] = None,
        max_age_hours: Optional[int] = None,
        snapshot_as_of: Optional[str] = None,
        filter_empty_results: Optional[bool] = None,
        subpages: Optional[int] = None,
        subpage_target: Optional[Union[str, List[str]]] = None,
        extras: Optional[ExtrasOptions] = None,
        timeout: Optional[float] = None,
        extra_headers: Optional[Mapping[str, Optional[str]]] = None,
        extra_query: Optional[Mapping[str, Any]] = None,
        extra_body: Optional[Mapping[str, Any]] = None,
    ) -> SearchResponse[ResultWithText]: ...

    @overload
    @deprecated(
        "find_similar_and_contents() is deprecated. Use search() instead; "
        "search() returns text contents by default."
    )
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
        category: Optional[Category] = None,
        flags: Optional[List[str]] = None,
        livecrawl_timeout: Optional[int] = None,
        livecrawl: Optional[LIVECRAWL_OPTIONS] = None,
        max_age_hours: Optional[int] = None,
        snapshot_as_of: Optional[str] = None,
        filter_empty_results: Optional[bool] = None,
        subpages: Optional[int] = None,
        subpage_target: Optional[Union[str, List[str]]] = None,
        extras: Optional[ExtrasOptions] = None,
        timeout: Optional[float] = None,
        extra_headers: Optional[Mapping[str, Optional[str]]] = None,
        extra_query: Optional[Mapping[str, Any]] = None,
        extra_body: Optional[Mapping[str, Any]] = None,
    ) -> SearchResponse[ResultWithText]: ...

    @overload
    @deprecated(
        "find_similar_and_contents() is deprecated. Use search() instead; "
        "search() returns text contents by default."
    )
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
        category: Optional[Category] = None,
        flags: Optional[List[str]] = None,
        livecrawl_timeout: Optional[int] = None,
        livecrawl: Optional[LIVECRAWL_OPTIONS] = None,
        max_age_hours: Optional[int] = None,
        snapshot_as_of: Optional[str] = None,
        filter_empty_results: Optional[bool] = None,
        subpages: Optional[int] = None,
        subpage_target: Optional[Union[str, List[str]]] = None,
        extras: Optional[ExtrasOptions] = None,
        timeout: Optional[float] = None,
        extra_headers: Optional[Mapping[str, Optional[str]]] = None,
        extra_query: Optional[Mapping[str, Any]] = None,
        extra_body: Optional[Mapping[str, Any]] = None,
    ) -> SearchResponse[ResultWithSummary]: ...

    @overload
    @deprecated(
        "find_similar_and_contents() is deprecated. Use search() instead; "
        "search() returns text contents by default."
    )
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
        category: Optional[Category] = None,
        flags: Optional[List[str]] = None,
        livecrawl_timeout: Optional[int] = None,
        livecrawl: Optional[LIVECRAWL_OPTIONS] = None,
        max_age_hours: Optional[int] = None,
        snapshot_as_of: Optional[str] = None,
        filter_empty_results: Optional[bool] = None,
        subpages: Optional[int] = None,
        subpage_target: Optional[Union[str, List[str]]] = None,
        extras: Optional[ExtrasOptions] = None,
        timeout: Optional[float] = None,
        extra_headers: Optional[Mapping[str, Optional[str]]] = None,
        extra_query: Optional[Mapping[str, Any]] = None,
        extra_body: Optional[Mapping[str, Any]] = None,
    ) -> SearchResponse[ResultWithTextAndSummary]: ...

    # Every content option the method accepts, for the calls the overloads above
    # do not cover (highlights, metadata, context, or False for text or
    # summary). The result type is not narrowed for them.
    @overload
    @deprecated(
        "find_similar_and_contents() is deprecated. Use search() instead; "
        "search() returns text contents by default."
    )
    def find_similar_and_contents(
        self,
        url: str,
        *,
        text: Optional[Union[TextContentsOptions, bool]] = None,
        summary: Optional[Union[SummaryContentsOptions, bool]] = None,
        highlights: Optional[Union[HighlightsContentsOptions, bool]] = None,
        metadata: Optional[Union[Dict[str, Any], bool]] = None,
        context: Optional[Union[ContextContentsOptions, bool]] = None,
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
        category: Optional[Category] = None,
        flags: Optional[List[str]] = None,
        livecrawl_timeout: Optional[int] = None,
        livecrawl: Optional[LIVECRAWL_OPTIONS] = None,
        max_age_hours: Optional[int] = None,
        snapshot_as_of: Optional[str] = None,
        filter_empty_results: Optional[bool] = None,
        subpages: Optional[int] = None,
        subpage_target: Optional[Union[str, List[str]]] = None,
        extras: Optional[ExtrasOptions] = None,
        timeout: Optional[float] = None,
        extra_headers: Optional[Mapping[str, Optional[str]]] = None,
        extra_query: Optional[Mapping[str, Any]] = None,
        extra_body: Optional[Mapping[str, Any]] = None,
    ) -> SearchResponse[Any]: ...

    @deprecated(
        "find_similar_and_contents() is deprecated. Use search() instead; "
        "search() returns text contents by default."
    )
    def find_similar_and_contents(self, url: str, **kwargs):
        """
        DEPRECATED: Use search() instead. The search() method returns text contents by default.

        Migration:
        - find_similar_and_contents(url) → search(f"pages similar to {url}")
        - find_similar_and_contents(url, text=True) → search(f"pages similar to {url}", contents={"text": True})
        - find_similar_and_contents(url, summary=True) → search(f"pages similar to {url}", contents={"summary": True})
        """

        timeout = kwargs.pop("timeout", None)
        extra_headers = kwargs.pop("extra_headers", None)
        extra_query = kwargs.pop("extra_query", None)
        extra_body = kwargs.pop("extra_body", None)
        options = {"url": url}
        for k, v in kwargs.items():
            if v is not None:
                options[k] = v
        # Default to text with max characters if none specified
        if "text" not in options and "summary" not in options:
            options["text"] = {"max_characters": DEFAULT_MAX_CHARACTERS}

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
        options = nest_fields(options, NESTED_CONTENTS_FIELDS, "contents")
        options = to_camel_case(options, skip_keys=["schema"])
        data = self.request(
            "/findSimilar",
            options,
            timeout=timeout,
            extra_headers=extra_headers,
            extra_query=extra_query,
            extra_body=extra_body,
        )
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
                    crawl_date=snake_result.get("crawl_date"),
                    snapshot_at=snake_result.get("snapshot_at"),
                    text=snake_result.get("text"),
                    summary=snake_result.get("summary"),
                    highlights=snake_result.get("highlights"),
                    highlight_scores=snake_result.get("highlight_scores"),
                    entities=_parse_entities(result.get("entities")),
                )
            )
        return SearchResponse(
            results,
            data.get("resolvedSearchType"),
            data.get("autoDate"),
            context=data.get("context"),  # DEPRECATED FIELD: legacy context response.
            cost_dollars=cost_dollars,
            search_time=data.get("searchTime"),
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
            num_results: Optional[int] = 3,
            include_domains: Optional[List[str]] = None,
            exclude_domains: Optional[List[str]] = None,
            start_crawl_date: Optional[str] = None,
            end_crawl_date: Optional[str] = None,
            start_published_date: Optional[str] = None,
            end_published_date: Optional[str] = None,
            include_text: Optional[List[str]] = None,
            exclude_text: Optional[List[str]] = None,
            type: Optional[Union[SearchType, str]] = None,
            category: Optional[Category] = None,
            result_max_len: int = 2048,
            flags: Optional[List[str]] = None,
            # OpenAI args
            **openai_kwargs,
        ):
            exa_kwargs = {
                "num_results": num_results,
                "include_domains": include_domains,
                "exclude_domains": exclude_domains,
                "start_crawl_date": start_crawl_date,
                "end_crawl_date": end_crawl_date,
                "start_published_date": start_published_date,
                "end_published_date": end_published_date,
                "include_text": include_text,
                "exclude_text": exclude_text,
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
            start_crawl_date=exa_kwargs.get("start_crawl_date"),
            end_crawl_date=exa_kwargs.get("end_crawl_date"),
            start_published_date=exa_kwargs.get("start_published_date"),
            end_published_date=exa_kwargs.get("end_published_date"),
            include_text=exa_kwargs.get("include_text"),
            exclude_text=exa_kwargs.get("exclude_text"),
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
        user_location: Optional[Union[str, UserLocation]] = None,
        user_identifier: Optional[str] = None,
        timeout: Optional[float] = None,
        extra_headers: Optional[Mapping[str, Optional[str]]] = None,
        extra_query: Optional[Mapping[str, Any]] = None,
        extra_body: Optional[Mapping[str, Any]] = None,
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
        user_location: Optional[Union[str, UserLocation]] = None,
        user_identifier: Optional[str] = None,
        timeout: Optional[float] = None,
        extra_headers: Optional[Mapping[str, Optional[str]]] = None,
        extra_query: Optional[Mapping[str, Any]] = None,
        extra_body: Optional[Mapping[str, Any]] = None,
    ) -> Union[AnswerResponse, StreamAnswerResponse]:
        """Generate an answer to a query using Exa's search and LLM capabilities.

        Args:
            query (str): The query to answer.
            text (bool, optional): Whether to include full text in the results. Defaults to False.
            system_prompt (str, optional): A system prompt to guide the LLM's behavior when generating the answer.
            model (str, optional): The model to use for answering. Defaults to None.
            output_schema (dict[str, Any], optional): JSON schema describing the desired answer structure.
            user_location (str | UserLocation, optional): The end user's location, as a
                two-letter ISO 3166-1 country code or a UserLocation dict.
            user_identifier (str, optional): An opaque ID you assign to the end user
                this request is made for, such as a UUID, used to attribute usage to
                that end user. Must not contain personal information such as an email
                address, phone number, username or name. Hash such values before
                sending them. 1 to 64 characters: letters, digits, ``_`` and ``-``.
                Retained even when your team has Zero Data Retention enabled. Does not
                affect results.
            timeout (float, optional): Timeout in seconds for this request. Defaults to the client-level timeout.
            extra_headers (Mapping[str, Optional[str]], optional): Extra headers to send with the request.
            extra_query (Mapping[str, Any], optional): Extra query parameters to send with the request.
            extra_body (Mapping[str, Any], optional): Extra fields merged over the JSON request body, except stream.

        Returns:
            AnswerResponse: An object containing the answer and citations.

        Raises:
            ValueError: If stream=True is provided. Use stream_answer() instead for streaming responses.

        Examples:
            response = exa.answer("What is the capital of France?")

            print(response.answer)       # e.g. "Paris"
            print(response.citations)    # list of citations used

            # If you want the full text of the citations in the response:
            response_with_text = exa.answer(
                "What is the capital of France?",
                text=True
            )
            print(response_with_text.citations[0].text)  # Full page text
        """
        if stream:
            raise ValueError(
                "stream=True is not supported in `answer()`. "
                "Please use `stream_answer(...)` for streaming."
            )

        _validate_user_location(user_location)
        options = {
            k: v
            for k, v in locals().items()
            if k not in _NON_BODY_ARGUMENTS and v is not None
        }

        # Convert output_schema if present
        if "output_schema" in options and options["output_schema"] is not None:
            options["output_schema"] = _convert_schema_input(options["output_schema"])

        options = to_camel_case(options, ["output_schema"])
        response = self.request(
            "/answer",
            options,
            timeout=timeout,
            extra_headers=extra_headers,
            extra_query=extra_query,
            extra_body=extra_body,
        )

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
        cost_dollars = parse_cost_dollars(response.get("costDollars"))
        return AnswerResponse(response["answer"], citations, cost_dollars)

    def stream_answer(
        self,
        query: str,
        *,
        text: bool = False,
        system_prompt: Optional[str] = None,
        model: Optional[Literal["exa", "exa-pro"]] = None,
        output_schema: Optional[JSONSchemaInput] = None,
        user_location: Optional[Union[str, UserLocation]] = None,
        user_identifier: Optional[str] = None,
        timeout: Optional[float] = None,
        extra_headers: Optional[Mapping[str, Optional[str]]] = None,
        extra_query: Optional[Mapping[str, Any]] = None,
        extra_body: Optional[Mapping[str, Any]] = None,
    ) -> StreamAnswerResponse:
        """Generate a streaming answer response.

        Args:
            query (str): The query to answer.
            text (bool): Whether to include full text in the results. Defaults to False.
            system_prompt (str, optional): A system prompt to guide the LLM's behavior when generating the answer.
            model (str, optional): The model to use for answering. Defaults to None.
            output_schema (dict[str, Any], optional): JSON schema describing the desired answer structure.
            user_location (str | UserLocation, optional): The end user's location, as a
                two-letter ISO 3166-1 country code or a UserLocation dict.
            user_identifier (str, optional): An opaque ID you assign to the end user
                this request is made for, such as a UUID, used to attribute usage to
                that end user. Must not contain personal information such as an email
                address, phone number, username or name. Hash such values before
                sending them. 1 to 64 characters: letters, digits, ``_`` and ``-``.
                Retained even when your team has Zero Data Retention enabled. Does not
                affect results.
            timeout (float, optional): Timeout in seconds for this request. Defaults to the client-level timeout.
                It bounds the wait for the stream to start. A stream that has started is not timed.
            extra_headers (Mapping[str, Optional[str]], optional): Extra headers to send with the request.
            extra_query (Mapping[str, Any], optional): Extra query parameters to send with the request.
            extra_body (Mapping[str, Any], optional): Extra fields merged over the JSON request body, except stream.

        Returns:
            StreamAnswerResponse: Iterating yields StreamChunk objects with partial text
                (``content``) and ``citations``. Once the stream has been read to the end,
                its ``cost_dollars`` holds the cost breakdown for this request.

        Examples:
            stream = exa.stream_answer("What is the capital of France?", text=True)

            for chunk in stream:
                if chunk.content:
                    print("Partial answer:", chunk.content)
                if chunk.citations:
                    for citation in chunk.citations:
                        print("Citation found:", citation.url)

            if stream.cost_dollars:
                print("Cost:", stream.cost_dollars.total)
        """
        _validate_user_location(user_location)
        options = {
            k: v
            for k, v in locals().items()
            if k not in _NON_BODY_ARGUMENTS and v is not None
        }

        # Convert output_schema if present
        if "output_schema" in options and options["output_schema"] is not None:
            options["output_schema"] = _convert_schema_input(options["output_schema"])

        options = to_camel_case(options, skip_keys=["output_schema"])
        options["stream"] = True
        raw_response = self.request(
            "/answer",
            options,
            timeout=timeout,
            extra_headers=extra_headers,
            extra_query=extra_query,
            extra_body=extra_body,
        )
        return StreamAnswerResponse(raw_response)


class AsyncExa(Exa):
    # The async clients that replace the sync ones `Exa.__init__` sets, declared
    # so that type checkers which take an attribute's type from the class that
    # first assigns it see the async types on AsyncExa.
    research: AsyncResearchClient  # type: ignore[assignment]
    websets: AsyncWebsetsClient  # type: ignore[assignment]
    monitors: AsyncSearchMonitorsClient  # type: ignore[assignment]
    agent: AsyncAgentNamespace  # type: ignore[assignment]
    beta: AsyncBetaClient  # type: ignore[assignment]
    tools: AsyncToolNamespace
    openai: AsyncOpenAINamespace
    anthropic: AsyncAnthropicNamespace
    _client: Optional[httpx.AsyncClient]

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base: str = "https://api.exa.ai",
        timeout: Optional[float] = DEFAULT_REQUEST_TIMEOUT,
    ):
        """Initialize the asynchronous Exa client.

        Args:
            api_key (str, optional): The API key for authenticating with the Exa API.
                Defaults to the EXA_API_KEY environment variable.
            api_base (str, optional): The base URL for the Exa API. Defaults to "https://api.exa.ai".
            timeout (float, optional): Default timeout in seconds for API requests.
                Defaults to 600. Pass ``None`` to disable. Methods that accept
                ``timeout`` can override this per call. Cancel in-flight requests
                by cancelling the awaiting asyncio task.

        Examples:
            >>> async with AsyncExa(api_key="your-api-key") as exa:
            ...     results = await exa.search("latest AI research papers")
        """
        super().__init__(api_key, api_base, timeout=timeout)
        # Override the synchronous ResearchClient with its async counterpart.
        self.research = AsyncResearchClient(self)
        # Override the synchronous WebsetsClient with its async counterpart.
        self.websets = AsyncWebsetsClient(self)
        # Override the synchronous SearchMonitorsClient with its async counterpart.
        self.monitors = AsyncSearchMonitorsClient(self)
        # Override the synchronous Agent clients with async counterparts.
        self.agent = AsyncAgentNamespace(self)
        self.beta = AsyncBetaClient(self)
        self._client = None
        self._tool_registry = _ToolRegistry()
        self.tools = AsyncToolNamespace(self, self._tool_registry)
        self.openai = AsyncOpenAINamespace(self, self._tool_registry)
        self.anthropic = AsyncAnthropicNamespace(self, self._tool_registry)

    @property
    def client(self) -> httpx.AsyncClient:
        # this may only be a
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url, headers=self.headers, timeout=self.timeout
            )
        return self._client

    async def aclose(self) -> None:
        """Close the HTTP connections this client keeps open.

        Call it when you are done with the client, or use the client as an
        ``async with`` block, which calls it on exit. A request made after it
        opens new connections.

        Examples:
            >>> exa = AsyncExa(api_key="your-api-key")
            >>> try:
            ...     results = await exa.search("latest AI research papers")
            ... finally:
            ...     await exa.aclose()
        """
        client, self._client = self._client, None
        if client is not None:
            await client.aclose()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        await self.aclose()

    @typed_timeouts
    async def async_request(
        self,
        endpoint: str,
        data=None,
        method: str = "POST",
        params=None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        extra_headers: Optional[Mapping[str, Optional[str]]] = None,
        extra_query: Optional[Mapping[str, Any]] = None,
        extra_body: Optional[Mapping[str, Any]] = None,
    ):
        """Send a request to the Exa API, optionally streaming if data['stream'] is True.

        Args:
            endpoint (str): The API endpoint (path).
            data (dict, optional): The JSON payload to send.
            method (str, optional): The HTTP method to use. Defaults to "POST".
            params (dict, optional): Query parameters.
            headers (Dict[str, str], optional): Additional headers to include in the request. Defaults to None.
            timeout (float, optional): Timeout in seconds for this request.
                Defaults to the client timeout. It bounds connecting and each wait
                for data from the server, not the whole call. For a streamed
                response it bounds the wait for the response to start. Once a
                successful response's headers have arrived, the stream is read
                with no timeout. An error response is read whole under it.
            extra_headers (Mapping[str, Optional[str]], optional): Extra headers. A header
                the client already sets is replaced, case-insensitively. Headers set to
                None are skipped. They do not change whether the response streams.
                ``data``, ``params`` and ``headers`` decide that. An
                ``Accept: text/event-stream`` set in ``headers``, as the Agent streams set
                it, stays. Any other ``Accept``, such as the default one the other streams
                send, is replaced.
            extra_query (Mapping[str, Any], optional): Extra query parameters, except
                ``stream``. Parameters set to None are skipped. On a GET request they
                are merged over ``params``.
            extra_body (Mapping[str, Any], optional): Extra fields merged over the JSON
                payload of a POST or PATCH request, except ``stream``.

        Returns:
            Union[dict, httpx.Response]: If streaming, returns the Response object.
            Otherwise, returns the JSON-decoded response as a dict.

        Raises:
            ValueError: If the request fails (non-200 status code), or a successful
                response's body is not JSON.
            ExaTimeoutError: If connecting, sending, waiting for the response to
                start, or waiting for more of a response that is not streamed
                exceeds the timeout. It is also an instance of the
                httpx.TimeoutException subclass HTTPX raised.
            TypeError: If ``extra_body`` is given with a pre-serialized string payload.
        """
        if method.upper() in ("POST", "PATCH"):
            data = merge_body(data, extra_body)
            warn_deprecated_fields(endpoint, data)
        # GET requests send `params` with the extra query merged over them; the
        # other methods send only the query string the call adds.
        extra_params = merge_query(None, extra_query)
        query_kwargs: Dict[str, Any] = {"params": extra_params} if extra_params else {}
        params = merge_query(params, extra_query)

        # Merge additional headers with existing headers
        request_headers = {**self.headers}
        if headers:
            request_headers.update(headers)

        # Check if we need streaming (either from data, params, or SSE Accept header).
        # Decided before the extra headers are applied: they change what is sent,
        # not how the response is read. merge_body and merge_query never take
        # `stream` from the extras for the same reason.
        needs_streaming = (
            (data and isinstance(data, dict) and data.get("stream"))
            or (params and params.get("stream") == "true")
            or request_headers.get("Accept") == "text/event-stream"
        )
        request_headers = merge_headers(request_headers, extra_headers)

        # Only pass the kwarg for per-call overrides; otherwise the
        # AsyncClient-level timeout (set on the constructor) applies.
        timeout_kwargs: Dict[str, Any] = {}
        if timeout is not None:
            timeout_kwargs["timeout"] = _validate_timeout(timeout)

        if method.upper() == "GET":
            if needs_streaming:
                request = self.client.build_request(
                    "GET",
                    self.base_url + endpoint,
                    params=params,
                    headers=request_headers,
                    **timeout_kwargs,
                )
                res = await self.client.send(request, stream=True)
                return await _started_async_stream(res)
            else:
                res = await self.client.get(
                    self.base_url + endpoint,
                    params=params,
                    headers=request_headers,
                    **timeout_kwargs,
                )
        elif method.upper() == "POST":
            if needs_streaming:
                request = self.client.build_request(
                    "POST",
                    self.base_url + endpoint,
                    json=data,
                    headers=request_headers,
                    **timeout_kwargs,
                    **query_kwargs,
                )
                res = await self.client.send(request, stream=True)
                return await _started_async_stream(res)
            else:
                res = await self.client.post(
                    self.base_url + endpoint,
                    json=data,
                    headers=request_headers,
                    **timeout_kwargs,
                    **query_kwargs,
                )
        elif method.upper() == "PATCH":
            res = await self.client.patch(
                self.base_url + endpoint,
                json=data,
                headers=request_headers,
                **timeout_kwargs,
                **query_kwargs,
            )
        elif method.upper() == "DELETE":
            res = await self.client.delete(
                self.base_url + endpoint,
                headers=request_headers,
                **timeout_kwargs,
                **query_kwargs,
            )
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        if res.status_code >= 400:
            raise ValueError(
                f"Request failed with status code {res.status_code}: {res.text}"
            )
        payload = _decode_json_body(res)
        issue_body_warnings(endpoint, method, payload, res.headers.get("x-request-id"))
        return payload

    async def search(
        self,
        query: str,
        *,
        stream: Optional[bool] = False,
        contents: Optional[Union[ContentsOptions, Literal[False]]] = None,
        num_results: Optional[int] = None,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        start_crawl_date: Optional[str] = None,
        end_crawl_date: Optional[str] = None,
        start_published_date: Optional[str] = None,
        end_published_date: Optional[str] = None,
        include_text: Optional[List[str]] = None,
        exclude_text: Optional[List[str]] = None,
        type: Optional[Union[SearchType, str]] = None,
        category: Optional[Category] = None,
        flags: Optional[List[str]] = None,
        moderation: Optional[bool] = None,
        user_location: Optional[Union[str, UserLocation]] = None,
        additional_queries: Optional[List[str]] = None,
        system_prompt: Optional[str] = None,
        output_schema: Optional[DeepOutputSchema] = None,
        objective: Optional[str] = None,
        user_identifier: Optional[str] = None,
        betas: Optional[Sequence[str]] = None,
        extra_body: Optional[Mapping[str, Any]] = None,
        timeout: Optional[float] = None,
        extra_headers: Optional[Mapping[str, Optional[str]]] = None,
        extra_query: Optional[Mapping[str, Any]] = None,

    ) -> SearchResponse[Result]:
        """Perform a search.

        For AI answers, RAG, and search previews, use ``contents={"highlights": True}``
        and read each result's ``highlights`` list. Exa dynamically chooses the
        number of characters based on each document's relevance to your query.
        No manual character budget is needed. Set ``max_characters`` only when
        your application requires a specific numeric character limit; otherwise
        keep ``highlights=True``. Do not use the deprecated ``num_sentences`` or
        ``highlights_per_url`` options.

        Request text when you need full-page content, or use contents=False for
        titles and URLs only. Omitting contents still returns text with 10,000
        max characters by default.

        Args:
            extra_body (Optional[Mapping[str, Any]]): Per-call body overrides, except stream.
            query (str): The query string.
            stream (bool, optional): If True, stream the synthesized search response.
                Use ``stream_search(...)`` instead of ``search(..., stream=True)``.
            contents (ContentsOptions | False, optional): Options for retrieving page contents.
                Defaults to {"text": {"maxCharacters": 10000}}. Use False to disable contents.
                For AI context, prefer {"highlights": True} for relevance-based sizing
                and read result.highlights. See ContentsOptions for all options.
            num_results (int, optional): Number of search results to return. Default 10.
            include_domains (List[str], optional): Domains to include in the search.
            exclude_domains (List[str], optional): Domains to exclude from the search.
            start_crawl_date (str, optional): Deprecated and will be removed in a future release. Only links crawled after this date.
            end_crawl_date (str, optional): Deprecated and will be removed in a future release. Only links crawled before this date.
            start_published_date (str, optional): Only links published after this date.
            end_published_date (str, optional): Only links published before this date.
            include_text (List[str], optional): Strings that must appear in the page text.
            exclude_text (List[str], optional): Strings that must not appear in the page text.
            type (SearchType, optional): Search type - 'auto' (default), 'fast',
                'deep-lite', 'deep', 'deep-reasoning', 'neural', 'instant', or 'lite'
                (beta: low-cost, reduced parameter set).
            category (Category, optional): Data category to focus on (e.g.
                'company', 'news', 'publication').
            flags (List[str], optional): Experimental flags for Exa usage.
            moderation (bool, optional): If True, the search results will be moderated for safety.
            user_location (str | UserLocation, optional): The end user's location, as a
                two-letter ISO 3166-1 country code or a UserLocation dict.
            additional_queries (List[str], optional): Alternative query formulations for deep search to skip
                automatic LLM-based query expansion. Max 5 queries. Only applicable when type is
                'deep-lite', 'deep', or 'deep-reasoning'.
                Example: ["machine learning", "ML algorithms", "neural networks"]
            system_prompt (str, optional): Instructions that guide both the search process and
                the final returned result. Use this to prefer certain sources, emphasize novelty,
                avoid duplicates, or constrain the response style. Supported for all search types.
            output_schema (DeepOutputSchema, optional): Search output schema for structured
                synthesis. When provided, the API returns synthesized output in ``output``.
                Use ``{"type": "text", "description": ...}`` for plain text output or
                ``{"type": "object", "properties": ..., "required": ...}`` for structured JSON.
                For object schemas, max nesting depth is 2 and max total properties is 10.
                Supported for all search types.
            objective (str, optional): The broader goal this search serves: the task the
                caller is working on, beyond the query itself. When an agent picks the query
                as one step of a larger task, pass the goal of that step: which documents
                should rank first, which should be excluded, and what to pull from them.
                Up to 4096 characters.
            user_identifier (str, optional): An opaque ID you assign to the end user
                this request is made for, such as a UUID, used to attribute usage to
                that end user. Must not contain personal information such as an email
                address, phone number, username or name. Hash such values before
                sending them. 1 to 64 characters: letters, digits, ``_`` and ``-``.
                Retained even when your team has Zero Data Retention enabled. Does not
                affect results.
            betas (Sequence[str], optional): Exa-Beta tokens to send with the request
                (e.g. ``[DYNAMIC_HIGHLIGHTS_BETA]`` for Dynamic Highlights).
            timeout (float, optional): Per-operation network inactivity timeout in seconds. Defaults to the client timeout.
            extra_headers (Mapping[str, Optional[str]], optional): Extra headers to send with the request.
            extra_query (Mapping[str, Any], optional): Extra query parameters to send with the request.

        Returns:
            SearchResponse: The response containing search results, etc.

        Raises:
            ValueError: If stream=True is provided. Use stream_search() instead.

        Examples:
            Basic async search:
            >>> async_exa = AsyncExa(api_key="your-api-key")
            >>> results = await async_exa.search(
            ...     "latest AI research papers", contents={"highlights": True}
            ... )
            >>> print(results.results[0].highlights)

            Async search with filters:
            >>> results = await async_exa.search(
            ...     "climate change research",
            ...     include_domains=["nature.com", "science.org"],
            ...     start_published_date="2024-01-01"
            ... )
        """
        if stream:
            raise ValueError(
                "stream=True is not supported in `search()`. "
                "Please use `stream_search(...)` for streaming."
            )

        options = {
            k: v
            for k, v in locals().items()
            if k not in _NON_BODY_ARGUMENTS and v is not None

        }
        options.pop("stream", None)
        options.pop("betas", None)

        # Handle contents parameter with default behavior
        if contents is False:
            # Explicitly no contents - remove from options
            options.pop("contents", None)
        elif contents is None and "contents" not in options:
            # No contents specified - add default text with 10,000 max characters
            options["contents"] = {"text": {"max_characters": DEFAULT_MAX_CHARACTERS}}
        elif contents is not None:
            # User provided contents - use as-is
            options["contents"] = contents

        _convert_contents_summary_schema(options)
        validate_search_options(options, SEARCH_OPTIONS_TYPES)
        options = to_camel_case(options, skip_keys=["output_schema", "schema"])
        options = _merge_search_body(options, extra_body)
        data = await self.async_request(
            "/search",
            options,
            headers=headers_for_betas(betas),
            timeout=timeout,
            extra_headers=extra_headers,
            extra_query=extra_query,
        )

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
                    crawl_date=snake_result.get("crawl_date"),
                    snapshot_at=snake_result.get("snapshot_at"),
                    text=snake_result.get("text"),
                    summary=snake_result.get("summary"),
                    highlights=snake_result.get("highlights"),
                    highlight_scores=snake_result.get("highlight_scores"),
                    entities=_parse_entities(result.get("entities")),
                )
            )
        return SearchResponse(
            results,
            data.get("resolvedSearchType"),
            data.get("autoDate"),
            context=data.get("context"),  # DEPRECATED FIELD: legacy context response.
            output=parse_deep_search_output(data.get("output")),
            cost_dollars=cost_dollars,
            search_time=data.get("searchTime"),
            warnings=parse_search_warnings(data.get("warnings")),
            notices=parse_search_notices(data.get("notices")),
        )

    async def stream_search(
        self,
        query: str,
        *,
        contents: Optional[Union[ContentsOptions, Literal[False]]] = None,
        num_results: Optional[int] = None,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        start_crawl_date: Optional[str] = None,
        end_crawl_date: Optional[str] = None,
        start_published_date: Optional[str] = None,
        end_published_date: Optional[str] = None,
        include_text: Optional[List[str]] = None,
        exclude_text: Optional[List[str]] = None,
        type: Optional[Union[SearchType, str]] = None,
        category: Optional[Category] = None,
        flags: Optional[List[str]] = None,
        moderation: Optional[bool] = None,
        user_location: Optional[Union[str, UserLocation]] = None,
        additional_queries: Optional[List[str]] = None,
        system_prompt: Optional[str] = None,
        output_schema: Optional[DeepOutputSchema] = None,
        objective: Optional[str] = None,
        user_identifier: Optional[str] = None,
        extra_body: Optional[Mapping[str, Any]] = None,
        timeout: Optional[float] = None,
        extra_headers: Optional[Mapping[str, Optional[str]]] = None,
        extra_query: Optional[Mapping[str, Any]] = None,

    ) -> AsyncStreamSearchResponse:
        """Generate a streaming search response asynchronously.

        Args:
            extra_body (Optional[Mapping[str, Any]]): Per-call body overrides, except stream.
            query (str): The query string.
            contents (ContentsOptions | False, optional): Options for retrieving page contents.
                Defaults to {"text": {"maxCharacters": 10000}}. Use False to disable contents.
            num_results (int, optional): Number of search results to return. Default 10.
            include_domains (List[str], optional): Domains to include in the search.
            exclude_domains (List[str], optional): Domains to exclude from the search.
            start_crawl_date (str, optional): Deprecated and will be removed in a future release. Only links crawled after this date.
            end_crawl_date (str, optional): Deprecated and will be removed in a future release. Only links crawled before this date.
            start_published_date (str, optional): Only links published after this date.
            end_published_date (str, optional): Only links published before this date.
            include_text (List[str], optional): Strings that must appear in the page text.
            exclude_text (List[str], optional): Strings that must not appear in the page text.
            type (SearchType, optional): Search type - 'auto' (default), 'fast',
                'deep-lite', 'deep', 'deep-reasoning', 'neural', or 'instant'.
            category (Category, optional): Data category to focus on.
            flags (List[str], optional): Experimental flags for Exa usage.
            moderation (bool, optional): If True, the search results will be moderated for safety.
            user_location (str | UserLocation, optional): The end user's location, as a
                two-letter ISO 3166-1 country code or a UserLocation dict.
            additional_queries (List[str], optional): Alternative query formulations for deep search.
            system_prompt (str, optional): Instructions that guide the search process and streamed synthesis.
            output_schema (DeepOutputSchema, optional): Search output schema for structured synthesis.
            objective (str, optional): The broader goal this search serves: the task the
                caller is working on, beyond the query itself. Up to 4096 characters.
            user_identifier (str, optional): An opaque ID you assign to the end user
                this request is made for, such as a UUID, used to attribute usage to
                that end user. Must not contain personal information such as an email
                address, phone number, username or name. Hash such values before
                sending them. 1 to 64 characters: letters, digits, ``_`` and ``-``.
                Retained even when your team has Zero Data Retention enabled. Does not
                affect results.
            timeout (float, optional): Timeout in seconds for this request. Defaults to the client-level timeout.
                It bounds the wait for the stream to start. A stream that has started is not timed.
            extra_headers (Mapping[str, Optional[str]], optional): Extra headers to send with the request.
            extra_query (Mapping[str, Any], optional): Extra query parameters to send with the request.


        Returns:
            AsyncStreamSearchResponse: An async iterator yielding OpenAI-style streaming chunks.
                When the API returns ``warnings`` about the request, one chunk after the
                text carries them. A search without ``output_schema`` has no text to
                stream. Its stream yields one chunk with the results as ``citations``,
                then the warnings chunk when the API returns warnings. Call ``search()``
                for every field of the results. Once the stream has been read to the
                end, its ``cost_dollars`` holds the cost breakdown for this request.

        Examples:
            >>> async_exa = AsyncExa(api_key="your-api-key")
            >>> stream = await async_exa.stream_search(
            ...     "What are the latest battery breakthroughs?",
            ...     type="auto",
            ...     output_schema={"type": "text"},
            ... )
            >>> async for chunk in stream:
            ...     if chunk.content:
            ...         print(chunk.content, end="", flush=True)
        """
        options = {
            k: v
            for k, v in locals().items()
            if k not in _NON_BODY_ARGUMENTS and v is not None

        }

        if contents is False:
            options.pop("contents", None)
        elif contents is None and "contents" not in options:
            options["contents"] = {"text": {"max_characters": DEFAULT_MAX_CHARACTERS}}
        elif contents is not None:
            options["contents"] = contents

        validate_search_options(options, SEARCH_OPTIONS_TYPES)
        options = to_camel_case(options, skip_keys=["output_schema"])
        options = _merge_search_body(options, extra_body, streaming=True)
        raw_response = await self.async_request(
            "/search",
            options,
            timeout=timeout,
            extra_headers=extra_headers,
            extra_query=extra_query,
        )

        return AsyncStreamSearchResponse(raw_response)

    @deprecated(
        "search_and_contents() is deprecated. Use search() instead; "
        "search() returns text contents by default."
    )
    async def search_and_contents(
        self,
        query: str,
        *,
        extra_body: Optional[Mapping[str, Any]] = None,
        extra_headers: Optional[Mapping[str, Optional[str]]] = None,
        extra_query: Optional[Mapping[str, Any]] = None,
        **kwargs: Any,
    ) -> SearchResponse[Result]:
        """
        DEPRECATED: Use search() instead. The search() method now returns text contents by default.

        Args:
            extra_body (Optional[Mapping[str, Any]]): Per-call body overrides, except stream.
            extra_headers (Mapping[str, Optional[str]], optional): Extra headers to send with the request.
            extra_query (Mapping[str, Any], optional): Extra query parameters to send with the request.

        Migration:
        - search_and_contents(query) → search(query)
        - search_and_contents(query, text=True) → search(query, contents={"text": True})
        - search_and_contents(query, summary=True) → search(query, contents={"summary": True})
        """

        timeout = kwargs.pop("timeout", None)
        options = {"query": query}
        for k, v in kwargs.items():
            if v is not None:
                options[k] = v
        # If user didn't ask for any particular content, default to text with max characters
        if (
            "text" not in options
            and "summary" not in options
            and "extras" not in options
        ):
            options["text"] = {"max_characters": DEFAULT_MAX_CHARACTERS}

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
        options = nest_fields(options, NESTED_CONTENTS_FIELDS, "contents")
        options = to_camel_case(options, skip_keys=["schema"])
        options = _merge_search_body(options, extra_body)
        data = await self.async_request(
            "/search",
            options,
            timeout=timeout,
            extra_headers=extra_headers,
            extra_query=extra_query,
        )

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
                    crawl_date=snake_result.get("crawl_date"),
                    snapshot_at=snake_result.get("snapshot_at"),
                    text=snake_result.get("text"),
                    summary=snake_result.get("summary"),
                    highlights=snake_result.get("highlights"),
                    highlight_scores=snake_result.get("highlight_scores"),
                    entities=_parse_entities(result.get("entities")),
                )
            )
        return SearchResponse(
            results,
            data.get("resolvedSearchType"),
            data.get("autoDate"),
            context=data.get("context"),  # DEPRECATED FIELD: legacy context response.
            cost_dollars=cost_dollars,
            search_time=data.get("searchTime"),
            warnings=parse_search_warnings(data.get("warnings")),
            notices=parse_search_notices(data.get("notices")),
        )

    @overload
    async def get_contents(
        self,
        urls: Union[str, List[str], List[_Result]],
        *,
        livecrawl_timeout: Optional[int] = None,
        livecrawl: Optional[LIVECRAWL_OPTIONS] = None,
        max_age_hours: Optional[int] = None,
        snapshot_as_of: Optional[str] = None,
        filter_empty_results: Optional[bool] = None,
        subpages: Optional[int] = None,
        subpage_target: Optional[Union[str, List[str]]] = None,
        extras: Optional[ExtrasOptions] = None,
        flags: Optional[List[str]] = None,
        user_identifier: Optional[str] = None,
        betas: Optional[Sequence[str]] = None,
        timeout: Optional[float] = None,
        extra_headers: Optional[Mapping[str, Optional[str]]] = None,
        extra_query: Optional[Mapping[str, Any]] = None,
        extra_body: Optional[Mapping[str, Any]] = None,
    ) -> SearchResponse[ResultWithText]: ...

    @overload
    async def get_contents(
        self,
        urls: Union[str, List[str], List[_Result]],
        *,
        text: Union[TextContentsOptions, Literal[True]],
        livecrawl_timeout: Optional[int] = None,
        livecrawl: Optional[LIVECRAWL_OPTIONS] = None,
        max_age_hours: Optional[int] = None,
        snapshot_as_of: Optional[str] = None,
        filter_empty_results: Optional[bool] = None,
        subpages: Optional[int] = None,
        subpage_target: Optional[Union[str, List[str]]] = None,
        extras: Optional[ExtrasOptions] = None,
        flags: Optional[List[str]] = None,
        user_identifier: Optional[str] = None,
        betas: Optional[Sequence[str]] = None,
        timeout: Optional[float] = None,
        extra_headers: Optional[Mapping[str, Optional[str]]] = None,
        extra_query: Optional[Mapping[str, Any]] = None,
        extra_body: Optional[Mapping[str, Any]] = None,
    ) -> SearchResponse[ResultWithText]: ...

    @overload
    async def get_contents(
        self,
        urls: Union[str, List[str], List[_Result]],
        *,
        summary: Union[SummaryContentsOptions, Literal[True]],
        livecrawl_timeout: Optional[int] = None,
        livecrawl: Optional[LIVECRAWL_OPTIONS] = None,
        max_age_hours: Optional[int] = None,
        snapshot_as_of: Optional[str] = None,
        filter_empty_results: Optional[bool] = None,
        subpages: Optional[int] = None,
        subpage_target: Optional[Union[str, List[str]]] = None,
        extras: Optional[ExtrasOptions] = None,
        flags: Optional[List[str]] = None,
        user_identifier: Optional[str] = None,
        betas: Optional[Sequence[str]] = None,
        timeout: Optional[float] = None,
        extra_headers: Optional[Mapping[str, Optional[str]]] = None,
        extra_query: Optional[Mapping[str, Any]] = None,
        extra_body: Optional[Mapping[str, Any]] = None,
    ) -> SearchResponse[ResultWithSummary]: ...

    @overload
    async def get_contents(
        self,
        urls: Union[str, List[str], List[_Result]],
        *,
        text: Union[TextContentsOptions, Literal[True]],
        summary: Union[SummaryContentsOptions, Literal[True]],
        livecrawl_timeout: Optional[int] = None,
        livecrawl: Optional[LIVECRAWL_OPTIONS] = None,
        max_age_hours: Optional[int] = None,
        snapshot_as_of: Optional[str] = None,
        filter_empty_results: Optional[bool] = None,
        subpages: Optional[int] = None,
        subpage_target: Optional[Union[str, List[str]]] = None,
        extras: Optional[ExtrasOptions] = None,
        flags: Optional[List[str]] = None,
        user_identifier: Optional[str] = None,
        betas: Optional[Sequence[str]] = None,
        timeout: Optional[float] = None,
        extra_headers: Optional[Mapping[str, Optional[str]]] = None,
        extra_query: Optional[Mapping[str, Any]] = None,
        extra_body: Optional[Mapping[str, Any]] = None,
    ) -> SearchResponse[ResultWithTextAndSummary]: ...

    # Every content option the method accepts, for the calls the overloads above
    # do not cover (highlights, metadata, context, or False for text or
    # summary). The result type is not narrowed for them.
    @overload
    async def get_contents(
        self,
        urls: Union[str, List[str], List[_Result]],
        *,
        text: Optional[Union[TextContentsOptions, bool]] = None,
        summary: Optional[Union[SummaryContentsOptions, bool]] = None,
        highlights: Optional[Union[HighlightsContentsOptions, bool]] = None,
        metadata: Optional[Union[Dict[str, Any], bool]] = None,
        context: Optional[Union[ContextContentsOptions, bool]] = None,
        livecrawl_timeout: Optional[int] = None,
        livecrawl: Optional[LIVECRAWL_OPTIONS] = None,
        max_age_hours: Optional[int] = None,
        snapshot_as_of: Optional[str] = None,
        filter_empty_results: Optional[bool] = None,
        subpages: Optional[int] = None,
        subpage_target: Optional[Union[str, List[str]]] = None,
        extras: Optional[ExtrasOptions] = None,
        flags: Optional[List[str]] = None,
        user_identifier: Optional[str] = None,
        betas: Optional[Sequence[str]] = None,
        timeout: Optional[float] = None,
        extra_headers: Optional[Mapping[str, Optional[str]]] = None,
        extra_query: Optional[Mapping[str, Any]] = None,
        extra_body: Optional[Mapping[str, Any]] = None,
    ) -> SearchResponse[Any]: ...

    async def get_contents(self, urls: Union[str, List[str], List[_Result]], **kwargs):
        """Retrieve contents for a list of URLs asynchronously.

        Args:
            urls (str | List[str] | List[Result]): A single URL, list of URLs, or list of Result objects.
            text (TextContentsOptions | True, optional): Options for text extraction.
            summary (SummaryContentsOptions | True, optional): Options for summary generation.
            max_age_hours (int, optional): Maximum age of cached content in hours. If content is older,
                it will be fetched fresh. Special values: 0 = always fetch fresh content,
                -1 = never fetch fresh (cache only). Example: 168 = fetch fresh for pages older than 7 days.
            livecrawl (str, optional): Deprecated. Use ``max_age_hours`` instead. Does not guarantee
                freshly fetched content. Cannot be combined with ``max_age_hours``.
            snapshot_as_of (str, optional): ISO 8601 datetime. Return the newest stored version at or before this instant instead of live content.
            filter_empty_results (bool, optional): Whether to filter out empty results.
            subpages (int, optional): Number of subpages to retrieve.
            subpage_target (str | List[str], optional): Target subpages to retrieve.
            extras (ExtrasOptions, optional): Options for extra content (links, image_links).
            flags (List[str], optional): Experimental flags.
            user_identifier (str, optional): An opaque ID you assign to the end user
                this request is made for, such as a UUID, used to attribute usage to
                that end user. Must not contain personal information such as an email
                address, phone number, username or name. Hash such values before
                sending them. 1 to 64 characters: letters, digits, ``_`` and ``-``.
                Retained even when your team has Zero Data Retention enabled. Does not
                affect results.
            betas (Sequence[str], optional): Exa-Beta tokens to send with the request
                (e.g. ``[DYNAMIC_HIGHLIGHTS_BETA]`` for Dynamic Highlights).
            timeout (float, optional): Per-operation network inactivity timeout in seconds. Defaults to the client timeout.
            extra_headers (Mapping[str, Optional[str]], optional): Extra headers to send with the request.
            extra_query (Mapping[str, Any], optional): Extra query parameters to send with the request.
            extra_body (Mapping[str, Any], optional): Extra fields merged over the JSON request body, except stream.

        Returns:
            SearchResponse[Result]: The response containing the contents of the URLs.

        Examples:
            Get contents for URLs asynchronously:
            >>> async_exa = AsyncExa(api_key="your-api-key")
            >>> results = await async_exa.get_contents("https://example.com/article")
            >>> print(results.results[0].text)

            Get contents from async search results:
            >>> search_results = await async_exa.search("AI news", contents=False)
            >>> contents = await async_exa.get_contents(search_results.results[:5])
        """
        # Normalize urls to always be a list
        if isinstance(urls, str):
            urls = [urls]
        elif isinstance(urls, list) and len(urls) > 0 and isinstance(urls[0], _Result):
            # Extract URLs from Result objects
            urls = [r.url for r in urls]

        betas = kwargs.pop("betas", None)
        timeout = kwargs.pop("timeout", None)
        extra_headers = kwargs.pop("extra_headers", None)
        extra_query = kwargs.pop("extra_query", None)
        extra_body = kwargs.pop("extra_body", None)

        options = {"urls": urls}
        for k, v in kwargs.items():
            if k != "self" and v is not None:
                options[k] = v

        if (
            "text" not in options
            and "summary" not in options
            and "extras" not in options
        ):
            options["text"] = {"max_characters": DEFAULT_MAX_CHARACTERS}

        merged_options = {}
        merged_options.update(CONTENTS_OPTIONS_TYPES)
        merged_options.update(CONTENTS_ENDPOINT_OPTIONS_TYPES)
        merged_options.update(CONTENTS_REQUEST_OPTIONS_TYPES)
        validate_search_options(options, merged_options)

        # Convert schema if present in summary options
        if "summary" in options and isinstance(options["summary"], dict):
            summary_opts = options["summary"]
            if "schema" in summary_opts:
                summary_opts["schema"] = _convert_schema_input(summary_opts["schema"])

        options = to_camel_case(options, ["schema"])
        data = await self.async_request(
            "/contents",
            options,
            headers=headers_for_betas(betas),
            timeout=timeout,
            extra_headers=extra_headers,
            extra_query=extra_query,
            extra_body=extra_body,
        )
        cost_dollars = parse_cost_dollars(data.get("costDollars"))
        statuses = [_parse_content_status(status) for status in data.get("statuses", [])]
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
                    crawl_date=snake_result.get("crawl_date"),
                    snapshot_at=snake_result.get("snapshot_at"),
                    text=snake_result.get("text"),
                    summary=snake_result.get("summary"),
                    highlights=snake_result.get("highlights"),
                    highlight_scores=snake_result.get("highlight_scores"),
                    entities=_parse_entities(result.get("entities")),
                )
            )
        return SearchResponse(
            results,
            data.get("resolvedSearchType"),
            data.get("autoDate"),
            context=data.get("context"),  # DEPRECATED FIELD: legacy context response.
            cost_dollars=cost_dollars,
            statuses=statuses,
            search_time=data.get("searchTime"),
        )

    @deprecated("find_similar()/findSimilar is deprecated. Use search() instead.")
    async def find_similar(
        self,
        url: str,
        *,
        contents: Optional[Union[ContentsOptions, Literal[False]]] = None,
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
        category: Optional[Category] = None,
        flags: Optional[List[str]] = None,
        timeout: Optional[float] = None,
        extra_headers: Optional[Mapping[str, Optional[str]]] = None,
        extra_query: Optional[Mapping[str, Any]] = None,
        extra_body: Optional[Mapping[str, Any]] = None,
    ) -> SearchResponse[Result]:
        """DEPRECATED METHOD: find_similar()/findSimilar is deprecated. Use search() instead.

        Migration:
            Use await search("pages similar to " + url) instead of await find_similar(url).

        Finds similar pages to a given URL, potentially with domain filters and date filters.

        By default, returns text contents with 10,000 max characters. Use contents=False to opt-out.

        Args:
            url (str): The URL to find similar pages for.
            contents (ContentsOptions | False, optional): Options for retrieving page contents.
                Defaults to {"text": {"maxCharacters": 10000}}. Use False to disable contents.
                See ContentsOptions for available options (text, highlights, summary, etc.).
            num_results (int, optional): Number of results to return. Default is None (server default).
            include_domains (List[str], optional): Domains to include in the search.
            exclude_domains (List[str], optional): Domains to exclude from the search.
            start_crawl_date (str, optional): Deprecated and will be removed in a future release. Only links crawled after this date.
            end_crawl_date (str, optional): Deprecated and will be removed in a future release. Only links crawled before this date.
            start_published_date (str, optional): Only links published after this date.
            end_published_date (str, optional): Only links published before this date.
            include_text (List[str], optional): Strings that must appear in the page text.
            exclude_text (List[str], optional): Strings that must not appear in the page text.
            exclude_source_domain (bool, optional): Whether to exclude the source domain.
            category (Category, optional): Data category to focus on (e.g.
                'company', 'news', 'publication').
            flags (List[str], optional): Experimental flags.
            timeout (float, optional): Timeout in seconds for this request. Defaults to the client-level timeout.
            extra_headers (Mapping[str, Optional[str]], optional): Extra headers to send with the request.
            extra_query (Mapping[str, Any], optional): Extra query parameters to send with the request.
            extra_body (Mapping[str, Any], optional): Extra fields merged over the JSON request body, except stream.

        Returns:
            SearchResponse[Result]

        Examples:
            Use async search instead:
            >>> async_exa = AsyncExa(api_key="your-api-key")
            >>> results = await async_exa.search("pages similar to https://www.nature.com/articles/s41586-021-03819-2")
            >>> print(results.results[0].title)

            Search with domain filters:
            >>> url = "https://arxiv.org/abs/2301.00001"
            >>> results = await async_exa.search(
            ...     f"pages similar to {url}",
            ...     include_domains=["arxiv.org", "openreview.net"],
            ... )
        """
        options = {
            k: v
            for k, v in locals().items()
            if k not in _NON_BODY_ARGUMENTS and v is not None
        }

        # Handle contents parameter with default behavior
        if contents is False:
            # Explicitly no contents - remove from options
            options.pop("contents", None)
        elif contents is None and "contents" not in options:
            # No contents specified - add default text with 10,000 max characters
            options["contents"] = {"text": {"max_characters": DEFAULT_MAX_CHARACTERS}}
        elif contents is not None:
            # User provided contents - use as-is
            options["contents"] = contents

        validate_search_options(options, FIND_SIMILAR_OPTIONS_TYPES)
        options = to_camel_case(options)
        data = await self.async_request(
            "/findSimilar",
            options,
            timeout=timeout,
            extra_headers=extra_headers,
            extra_query=extra_query,
            extra_body=extra_body,
        )
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
                    crawl_date=snake_result.get("crawl_date"),
                    snapshot_at=snake_result.get("snapshot_at"),
                    text=snake_result.get("text"),
                    summary=snake_result.get("summary"),
                    highlights=snake_result.get("highlights"),
                    highlight_scores=snake_result.get("highlight_scores"),
                    entities=_parse_entities(result.get("entities")),
                )
            )
        return SearchResponse(
            results,
            data.get("resolvedSearchType"),
            data.get("autoDate"),
            cost_dollars=cost_dollars,
            search_time=data.get("searchTime"),
        )

    @overload
    @deprecated(
        "find_similar_and_contents() is deprecated. Use search() instead; "
        "search() returns text contents by default."
    )
    async def find_similar_and_contents(
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
        category: Optional[Category] = None,
        flags: Optional[List[str]] = None,
        livecrawl_timeout: Optional[int] = None,
        livecrawl: Optional[LIVECRAWL_OPTIONS] = None,
        max_age_hours: Optional[int] = None,
        snapshot_as_of: Optional[str] = None,
        filter_empty_results: Optional[bool] = None,
        subpages: Optional[int] = None,
        subpage_target: Optional[Union[str, List[str]]] = None,
        extras: Optional[ExtrasOptions] = None,
        timeout: Optional[float] = None,
        extra_headers: Optional[Mapping[str, Optional[str]]] = None,
        extra_query: Optional[Mapping[str, Any]] = None,
        extra_body: Optional[Mapping[str, Any]] = None,
    ) -> SearchResponse[ResultWithText]: ...

    @overload
    @deprecated(
        "find_similar_and_contents() is deprecated. Use search() instead; "
        "search() returns text contents by default."
    )
    async def find_similar_and_contents(
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
        category: Optional[Category] = None,
        flags: Optional[List[str]] = None,
        livecrawl_timeout: Optional[int] = None,
        livecrawl: Optional[LIVECRAWL_OPTIONS] = None,
        max_age_hours: Optional[int] = None,
        snapshot_as_of: Optional[str] = None,
        filter_empty_results: Optional[bool] = None,
        subpages: Optional[int] = None,
        subpage_target: Optional[Union[str, List[str]]] = None,
        extras: Optional[ExtrasOptions] = None,
        timeout: Optional[float] = None,
        extra_headers: Optional[Mapping[str, Optional[str]]] = None,
        extra_query: Optional[Mapping[str, Any]] = None,
        extra_body: Optional[Mapping[str, Any]] = None,
    ) -> SearchResponse[ResultWithText]: ...

    @overload
    @deprecated(
        "find_similar_and_contents() is deprecated. Use search() instead; "
        "search() returns text contents by default."
    )
    async def find_similar_and_contents(
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
        category: Optional[Category] = None,
        flags: Optional[List[str]] = None,
        livecrawl_timeout: Optional[int] = None,
        livecrawl: Optional[LIVECRAWL_OPTIONS] = None,
        max_age_hours: Optional[int] = None,
        snapshot_as_of: Optional[str] = None,
        filter_empty_results: Optional[bool] = None,
        subpages: Optional[int] = None,
        subpage_target: Optional[Union[str, List[str]]] = None,
        extras: Optional[ExtrasOptions] = None,
        timeout: Optional[float] = None,
        extra_headers: Optional[Mapping[str, Optional[str]]] = None,
        extra_query: Optional[Mapping[str, Any]] = None,
        extra_body: Optional[Mapping[str, Any]] = None,
    ) -> SearchResponse[ResultWithSummary]: ...

    @overload
    @deprecated(
        "find_similar_and_contents() is deprecated. Use search() instead; "
        "search() returns text contents by default."
    )
    async def find_similar_and_contents(
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
        category: Optional[Category] = None,
        flags: Optional[List[str]] = None,
        livecrawl_timeout: Optional[int] = None,
        livecrawl: Optional[LIVECRAWL_OPTIONS] = None,
        max_age_hours: Optional[int] = None,
        snapshot_as_of: Optional[str] = None,
        filter_empty_results: Optional[bool] = None,
        subpages: Optional[int] = None,
        subpage_target: Optional[Union[str, List[str]]] = None,
        extras: Optional[ExtrasOptions] = None,
        timeout: Optional[float] = None,
        extra_headers: Optional[Mapping[str, Optional[str]]] = None,
        extra_query: Optional[Mapping[str, Any]] = None,
        extra_body: Optional[Mapping[str, Any]] = None,
    ) -> SearchResponse[ResultWithTextAndSummary]: ...

    # Every content option the method accepts, for the calls the overloads above
    # do not cover (highlights, metadata, context, or False for text or
    # summary). The result type is not narrowed for them.
    @overload
    @deprecated(
        "find_similar_and_contents() is deprecated. Use search() instead; "
        "search() returns text contents by default."
    )
    async def find_similar_and_contents(
        self,
        url: str,
        *,
        text: Optional[Union[TextContentsOptions, bool]] = None,
        summary: Optional[Union[SummaryContentsOptions, bool]] = None,
        highlights: Optional[Union[HighlightsContentsOptions, bool]] = None,
        metadata: Optional[Union[Dict[str, Any], bool]] = None,
        context: Optional[Union[ContextContentsOptions, bool]] = None,
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
        category: Optional[Category] = None,
        flags: Optional[List[str]] = None,
        livecrawl_timeout: Optional[int] = None,
        livecrawl: Optional[LIVECRAWL_OPTIONS] = None,
        max_age_hours: Optional[int] = None,
        snapshot_as_of: Optional[str] = None,
        filter_empty_results: Optional[bool] = None,
        subpages: Optional[int] = None,
        subpage_target: Optional[Union[str, List[str]]] = None,
        extras: Optional[ExtrasOptions] = None,
        timeout: Optional[float] = None,
        extra_headers: Optional[Mapping[str, Optional[str]]] = None,
        extra_query: Optional[Mapping[str, Any]] = None,
        extra_body: Optional[Mapping[str, Any]] = None,
    ) -> SearchResponse[Any]: ...

    @deprecated(
        "find_similar_and_contents() is deprecated. Use search() instead; "
        "search() returns text contents by default."
    )
    async def find_similar_and_contents(self, url: str, **kwargs):
        """
        DEPRECATED: Use search() instead. The search() method returns text contents by default.

        Migration:
        - find_similar_and_contents(url) → search(f"pages similar to {url}")
        - find_similar_and_contents(url, text=True) → search(f"pages similar to {url}", contents={"text": True})
        - find_similar_and_contents(url, summary=True) → search(f"pages similar to {url}", contents={"summary": True})
        """
        timeout = kwargs.pop("timeout", None)
        extra_headers = kwargs.pop("extra_headers", None)
        extra_query = kwargs.pop("extra_query", None)
        extra_body = kwargs.pop("extra_body", None)
        options = {"url": url}
        for k, v in kwargs.items():
            if v is not None:
                options[k] = v
        # Default to text with max characters if none specified
        if "text" not in options and "summary" not in options:
            options["text"] = {"max_characters": DEFAULT_MAX_CHARACTERS}

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
        options = nest_fields(options, NESTED_CONTENTS_FIELDS, "contents")
        options = to_camel_case(options, skip_keys=["schema"])
        data = await self.async_request(
            "/findSimilar",
            options,
            timeout=timeout,
            extra_headers=extra_headers,
            extra_query=extra_query,
            extra_body=extra_body,
        )
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
                    crawl_date=snake_result.get("crawl_date"),
                    snapshot_at=snake_result.get("snapshot_at"),
                    text=snake_result.get("text"),
                    summary=snake_result.get("summary"),
                    highlights=snake_result.get("highlights"),
                    highlight_scores=snake_result.get("highlight_scores"),
                    entities=_parse_entities(result.get("entities")),
                )
            )
        return SearchResponse(
            results,
            data.get("resolvedSearchType"),
            data.get("autoDate"),
            context=data.get("context"),  # DEPRECATED FIELD: legacy context response.
            cost_dollars=cost_dollars,
            search_time=data.get("searchTime"),
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
        user_location: Optional[Union[str, UserLocation]] = None,
        user_identifier: Optional[str] = None,
        timeout: Optional[float] = None,
        extra_headers: Optional[Mapping[str, Optional[str]]] = None,
        extra_query: Optional[Mapping[str, Any]] = None,
        extra_body: Optional[Mapping[str, Any]] = None,
    ) -> Union[AnswerResponse, StreamAnswerResponse]:
        """Generate an answer to a query using Exa's search and LLM capabilities.

        Args:
            query (str): The query to answer.
            text (bool, optional): Whether to include full text in the results. Defaults to False.
            system_prompt (str, optional): A system prompt to guide the LLM's behavior when generating the answer.
            model (str, optional): The model to use for answering. Defaults to None.
            output_schema (dict[str, Any], optional): JSON schema describing the desired answer structure.
            user_location (str | UserLocation, optional): The end user's location, as a
                two-letter ISO 3166-1 country code or a UserLocation dict.
            user_identifier (str, optional): An opaque ID you assign to the end user
                this request is made for, such as a UUID, used to attribute usage to
                that end user. Must not contain personal information such as an email
                address, phone number, username or name. Hash such values before
                sending them. 1 to 64 characters: letters, digits, ``_`` and ``-``.
                Retained even when your team has Zero Data Retention enabled. Does not
                affect results.
            timeout (float, optional): Timeout in seconds for this request. Defaults to the client-level timeout.
            extra_headers (Mapping[str, Optional[str]], optional): Extra headers to send with the request.
            extra_query (Mapping[str, Any], optional): Extra query parameters to send with the request.
            extra_body (Mapping[str, Any], optional): Extra fields merged over the JSON request body, except stream.

        Returns:
            AnswerResponse: An object containing the answer and citations.

        Raises:
            ValueError: If stream=True is provided. Use stream_answer() instead for streaming responses.

        Examples:
            Basic async question answering:
            >>> async_exa = AsyncExa(api_key="your-api-key")
            >>> response = await async_exa.answer("What are the latest developments in quantum computing?")
            >>> print(response.answer)

            Async answer with citations:
            >>> response = await async_exa.answer("Explain renewable energy benefits", text=True)
            >>> for citation in response.citations:
            ...     print(f"{citation.title}: {citation.url}")
        """
        if stream:
            raise ValueError(
                "stream=True is not supported in `answer()`. "
                "Please use `stream_answer(...)` for streaming."
            )

        _validate_user_location(user_location)
        options = {
            k: v
            for k, v in locals().items()
            if k not in _NON_BODY_ARGUMENTS and v is not None
        }

        # Convert output_schema if present
        if "output_schema" in options and options["output_schema"] is not None:
            options["output_schema"] = _convert_schema_input(options["output_schema"])

        options = to_camel_case(options, skip_keys=["output_schema"])
        response = await self.async_request(
            "/answer",
            options,
            timeout=timeout,
            extra_headers=extra_headers,
            extra_query=extra_query,
            extra_body=extra_body,
        )

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
        cost_dollars = parse_cost_dollars(response.get("costDollars"))
        return AnswerResponse(response["answer"], citations, cost_dollars)

    async def stream_answer(
        self,
        query: str,
        *,
        text: bool = False,
        system_prompt: Optional[str] = None,
        model: Optional[Literal["exa", "exa-pro"]] = None,
        output_schema: Optional[JSONSchemaInput] = None,
        user_location: Optional[Union[str, UserLocation]] = None,
        user_identifier: Optional[str] = None,
        timeout: Optional[float] = None,
        extra_headers: Optional[Mapping[str, Optional[str]]] = None,
        extra_query: Optional[Mapping[str, Any]] = None,
        extra_body: Optional[Mapping[str, Any]] = None,
    ) -> AsyncStreamAnswerResponse:
        """Generate a streaming answer response.

        Args:
            query (str): The query to answer.
            text (bool): Whether to include full text in the results. Defaults to False.
            system_prompt (str, optional): A system prompt to guide the LLM's behavior when generating the answer.
            model (str, optional): The model to use for answering. Defaults to None.
            output_schema (dict[str, Any], optional): JSON schema describing the desired answer structure.
            user_location (str | UserLocation, optional): The end user's location, as a
                two-letter ISO 3166-1 country code or a UserLocation dict.
            user_identifier (str, optional): An opaque ID you assign to the end user
                this request is made for, such as a UUID, used to attribute usage to
                that end user. Must not contain personal information such as an email
                address, phone number, username or name. Hash such values before
                sending them. 1 to 64 characters: letters, digits, ``_`` and ``-``.
                Retained even when your team has Zero Data Retention enabled. Does not
                affect results.
            timeout (float, optional): Timeout in seconds for this request. Defaults to the client-level timeout.
                It bounds the wait for the stream to start. A stream that has started is not timed.
            extra_headers (Mapping[str, Optional[str]], optional): Extra headers to send with the request.
            extra_query (Mapping[str, Any], optional): Extra query parameters to send with the request.
            extra_body (Mapping[str, Any], optional): Extra fields merged over the JSON request body, except stream.

        Returns:
            AsyncStreamAnswerResponse: Iterating with ``async for`` yields StreamChunk objects
                with partial text (``content``) and ``citations``. Once the stream has been
                read to the end, its ``cost_dollars`` holds the cost breakdown for this request.

        Examples:
            Stream an answer asynchronously:
            >>> async_exa = AsyncExa(api_key="your-api-key")
            >>> stream = await async_exa.stream_answer("What is quantum computing?")
            >>> async for chunk in stream:
            ...     if chunk.content:
            ...         print(chunk.content, end="", flush=True)

            Async stream with citations and cost:
            >>> stream = await async_exa.stream_answer("Explain climate change", text=True)
            >>> async for chunk in stream:
            ...     if chunk.content:
            ...         print(chunk.content, end="")
            ...     if chunk.citations:
            ...         print(f"\\nCitations: {[c.url for c in chunk.citations]}")
            >>> if stream.cost_dollars:
            ...     print(f"\\nCost: {stream.cost_dollars.total}")
        """
        _validate_user_location(user_location)
        options = {
            k: v
            for k, v in locals().items()
            if k not in _NON_BODY_ARGUMENTS and v is not None
        }

        # Convert output_schema if present
        if "output_schema" in options and options["output_schema"] is not None:
            options["output_schema"] = _convert_schema_input(options["output_schema"])

        options = to_camel_case(options, skip_keys=["output_schema"])
        options["stream"] = True
        raw_response = await self.async_request(
            "/answer",
            options,
            timeout=timeout,
            extra_headers=extra_headers,
            extra_query=extra_query,
            extra_body=extra_body,
        )
        return AsyncStreamAnswerResponse(raw_response)
