"""Warnings the Exa API returns about a request, and the Python warnings the SDK issues for them.

- `ExaWarning` is the Python warning the SDK issues for one `ApiWarning` (see
  `exa_py.api`), a warning the API returns about a request, with the request
  it is about.
- `issue_body_warnings` issues an `ExaWarning` for each warning in a response
  body or stream payload, through Python's `warnings` module, so the default
  filter shows a given warning once per line of calling code and
  `warnings.filterwarnings` or `logging.captureWarnings(True)` silences or
  routes it. `request` and `async_request` call it for every JSON response and
  the search stream for every payload, so every endpoint reports through it.
- `warn_deprecated_fields` issues a `DeprecationWarning` before a request for
  each deprecated field its body carries, whether the call set it as an
  option or through `extra_body`.

Both attribute the warning to the first frame outside this package, so it
points at the caller's own line rather than at SDK internals.
"""

from __future__ import annotations

import sys
import warnings
from typing import TYPE_CHECKING, Any, Mapping, Optional

if TYPE_CHECKING:
    from .api import ApiWarning

_PACKAGE = __name__.split(".")[0]

# Modules whose `deprecated` decorators wrap SDK methods (`warnings` on Python
# 3.13+, `typing_extensions` before).
_WRAPPER_MODULES = frozenset({"warnings", "typing_extensions"})

# Deprecated request fields, by their names in the request body, with the
# advice each DeprecationWarning gives under the SDK's option name.
_DEPRECATED_TOP_LEVEL_FIELDS = {
    "startCrawlDate": "start_crawl_date is deprecated and will be removed in a future release. Remove it from the request.",
    "endCrawlDate": "end_crawl_date is deprecated and will be removed in a future release. Remove it from the request.",
}
_DEPRECATED_HIGHLIGHTS_FIELDS = {
    "numSentences": "highlights num_sentences is deprecated. Use max_characters instead.",
    "highlightsPerUrl": "highlights highlights_per_url is deprecated. Use max_characters instead.",
}

# The endpoints whose request bodies take those fields.
_DEPRECATION_CHECKED_ENDPOINTS = frozenset({"/search", "/contents", "/findSimilar"})


class ExaWarning(UserWarning):
    """A warning the Exa API returned about a request, such as a field it ignores.

    The SDK issues one through Python's `warnings` module for each warning in a
    response, attributed to the line of your code that made the call. Python's
    default warnings filter shows a given warning once per calling line.
    `warnings.filterwarnings("ignore", category=ExaWarning)` silences them, and
    `logging.captureWarnings(True)` routes them to the `py.warnings` logger.
    The response keeps its own `warnings` whatever the filter does.

    Attributes:
        warning (ApiWarning): The warning, with its `code`, `path` (a JSON
            Pointer to the request field) and `message`.
        endpoint (str): API path the request was sent to, such as '/search'.
        method (str): HTTP method of the request, in upper case, such as 'POST'.
        request_id (str, optional): The request's id, when the response
            carried one.

    Examples:
        >>> import warnings
        >>> warnings.filterwarnings("ignore", category=ExaWarning)  # silence them
        >>> import logging
        >>> logging.captureWarnings(True)  # or route them to the `py.warnings` logger
    """

    warning: ApiWarning
    endpoint: str
    method: str
    request_id: Optional[str]

    def __init__(
        self,
        warning: ApiWarning,
        endpoint: str,
        method: str,
        request_id: Optional[str] = None,
    ):
        super().__init__(f"[exa] {method} {endpoint} {warning.code} at {warning.path}: {warning.message}")
        self.warning = warning
        self.endpoint = endpoint
        self.method = method
        self.request_id = request_id

    def __reduce__(self):
        return (type(self), (self.warning, self.endpoint, self.method, self.request_id))


def _is_internal_frame(frame: Any) -> bool:
    """Whether a frame belongs to this package or to a decorator wrapping its methods."""
    module = frame.f_globals.get("__name__", "")
    return module == _PACKAGE or module.startswith(_PACKAGE + ".") or module in _WRAPPER_MODULES


def _caller_stacklevel() -> int:
    """The `stacklevel` that attributes a warning to the first frame outside the SDK.

    Meant to be called by the function that calls `warnings.warn`: level 1 is
    that function, and each SDK frame above it adds one.
    """
    frame = sys._getframe(2)
    level = 2
    while frame is not None and _is_internal_frame(frame):
        frame = frame.f_back
        level += 1
    return level


# Endpoints whose responses carry a top-level `warnings` array of ApiWarnings.
# The SDK reads `warnings` from these alone, because other endpoints use the
# name for other shapes: agent monitor refresh events carry it as strings.
_BODY_WARNING_ENDPOINTS = frozenset({"/search"})


def issue_body_warnings(
    endpoint: str,
    method: str,
    body: Any,
    request_id: Optional[str] = None,
) -> None:
    """Issue an `ExaWarning` for each warning in a response body or stream payload.

    Args:
        endpoint: API path the request was sent to; only endpoints that return
            ApiWarnings are read.
        method: HTTP method of the request.
        body: The decoded response body or stream payload.
        request_id: The response's `x-request-id` header, used when the body
            carries no `requestId`.
    """
    if endpoint not in _BODY_WARNING_ENDPOINTS or not isinstance(body, Mapping):
        return
    # Imported here because .api imports this module.
    from .api import parse_api_warnings

    items = parse_api_warnings(body.get("warnings"))
    if not items:
        return
    body_request_id = body.get("requestId")
    if isinstance(body_request_id, str):
        request_id = body_request_id
    stacklevel = _caller_stacklevel()
    for item in items:
        warnings.warn(ExaWarning(item, endpoint, method.upper(), request_id), stacklevel=stacklevel)


def warn_deprecated_fields(endpoint: str, body: Any) -> None:
    """Issue a `DeprecationWarning` for each deprecated field in a request body.

    Reads the body as it is sent, after `extra_body` is merged, so a field
    set either way is caught and one an override removed is not. Checks the
    top-level fields and the highlights fields, whether highlights sit at the
    top level (/contents) or under `contents`.

    Args:
        endpoint: The API path the body is sent to; other endpoints are skipped.
        body: The request body, with the API's camelCase field names.
    """
    if endpoint not in _DEPRECATION_CHECKED_ENDPOINTS or not isinstance(body, Mapping):
        return
    messages = [
        message for field, message in _DEPRECATED_TOP_LEVEL_FIELDS.items() if body.get(field) is not None
    ]
    contents = body.get("contents")
    for highlights in (
        body.get("highlights"),
        contents.get("highlights") if isinstance(contents, Mapping) else None,
    ):
        if isinstance(highlights, Mapping):
            messages.extend(
                message
                for field, message in _DEPRECATED_HIGHLIGHTS_FIELDS.items()
                if highlights.get(field) is not None
            )
    if messages:
        stacklevel = _caller_stacklevel()
        for message in messages:
            warnings.warn(message, DeprecationWarning, stacklevel=stacklevel)
