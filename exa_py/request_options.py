"""Per-call request options accepted by every client method.

`ExtraRequestOptions` names the three keyword arguments a caller can add to any
API call: `extra_headers`, `extra_query` and `extra_body`. They add to the
request a method builds, for fields this SDK does not type yet.

`merge_headers`, `merge_query` and `merge_body` apply them. `Exa.request` and
`AsyncExa.async_request` call those, so every client method that forwards the
options behaves the same way. Sub-client methods collect the options as
``**extra`` and hand them to their client's ``request``, which checks them
with `given_request_options`.

The options change what is sent, never how the SDK reads the answer: the method
called decides whether the response streams and which page a listing fetches
next. So ``stream`` is not taken from `extra_body` or `extra_query`, an extra
``Accept`` header does not switch a call to streaming, and
`options_for_next_page` keeps a listing's cursor advancing.
"""

from typing import Any, Dict, Mapping, Optional, Union

from typing_extensions import TypedDict


class ExtraRequestOptions(TypedDict, total=False):
    """Keyword arguments every API method accepts on top of its own.

    Each adds to the request the method builds. On a name the method also
    sets, the value given here wins.

    Attributes:
        extra_headers: Extra HTTP headers. A header the SDK also sets is
            replaced, whatever its case. One set to None is skipped, so the
            SDK's own value is sent. An extra ``Accept`` never makes a call
            stream. The Agent streams keep the ``Accept: text/event-stream``
            they send, and any other ``Accept`` is replaced.
        extra_query: Extra query parameters, merged over the request's own,
            except ``stream``. One set to None is skipped, and True and False
            are sent as ``true`` and ``false``, inside lists too, where None
            elements are skipped. A ``cursor`` given to a helper that pages
            through a listing selects its first page only.
        extra_body: Extra fields merged over the JSON request body, except
            ``stream``, because the method called decides whether the response
            streams. Sent with requests that carry a JSON body (``POST`` and
            ``PATCH``). Other requests take ``extra_query`` instead.

    Examples:
        >>> exa.get_contents(
        ...     "https://example.com",
        ...     extra_body={"futureField": True},
        ...     extra_headers={"X-Request-Source": "nightly"},
        ... )
    """

    extra_headers: Optional[Mapping[str, Optional[str]]]
    extra_query: Optional[Mapping[str, Any]]
    extra_body: Optional[Mapping[str, Any]]


_OPTION_NAMES = frozenset(ExtraRequestOptions.__annotations__)


def given_request_options(extra: Mapping[str, Any]) -> ExtraRequestOptions:
    """Return the request options in `extra` that are set.

    A method that takes ``**extra`` accepts any keyword at the call, so this
    is where an unknown one is rejected, the way explicit parameters would
    reject it. Options left as None are dropped, so they are not forwarded.

    Raises:
        TypeError: If `extra` holds a keyword that is not a request option.
    """
    for name in extra:
        if name not in _OPTION_NAMES:
            raise TypeError(f"got an unexpected keyword argument '{name}'")
    return {name: value for name, value in extra.items() if value is not None}  # type: ignore[return-value]


def _accepts_event_stream(headers: Mapping[str, str]) -> bool:
    """Return whether `headers` ask for a server-sent event stream."""
    return any(
        name.lower() == "accept"
        and isinstance(value, str)
        and "text/event-stream" in value.lower()
        for name, value in headers.items()
    )


def merge_headers(
    headers: Mapping[str, str],
    extra_headers: Optional[Mapping[str, Optional[str]]],
) -> Dict[str, str]:
    """Return `headers` with `extra_headers` set on top.

    Header names are case-insensitive, so an extra header replaces every
    header already present under any casing instead of being sent beside it.
    An extra header set to None is skipped, so both HTTP stacks treat it alike:
    the async client sends its default headers from the HTTPX client itself,
    where a request cannot remove them. When `headers` ask for an event stream,
    an extra ``Accept`` is skipped too: the method called decides whether the
    response streams.
    """
    merged = dict(headers)
    keeps_accept = _accepts_event_stream(merged)
    for name, value in (extra_headers or {}).items():
        lower_case_name = name.lower()
        if value is None or (keeps_accept and lower_case_name == "accept"):
            continue
        merged = {
            existing: existing_value
            for existing, existing_value in merged.items()
            if existing.lower() != lower_case_name
        }
        merged[name] = value
    return merged


def _query_value(value: Any) -> Any:
    """Return `value` as both HTTP stacks should send it: booleans as JSON spells them.

    Requests sends True as ``True`` and HTTPX as ``true``; the API and the
    JavaScript SDK use ``true``. A list or tuple is sent as one parameter per
    element, so the same applies to each element, and an element set to None
    is skipped: Requests leaves it out, where HTTPX would send it empty.
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, tuple)):
        return [_query_value(element) for element in value if element is not None]
    return value


def merge_query(
    params: Optional[Mapping[str, Any]], extra_query: Optional[Mapping[str, Any]]
) -> Optional[Dict[str, Any]]:
    """Return the query parameters to send: `params` with `extra_query` merged over them.

    ``stream`` is never taken from `extra_query`, and a parameter set to None
    is skipped rather than clearing the request's own, as is a None element
    of a list value. True and False are sent as ``true`` and ``false`` by both
    clients, inside lists too. Returns `params` itself when there is nothing
    to add.
    """
    extra = {
        key: _query_value(value)
        for key, value in (extra_query or {}).items()
        if key != "stream" and value is not None
    }
    if not extra:
        return params  # type: ignore[return-value]
    return {**(params or {}), **extra}


def options_for_next_page(extra: ExtraRequestOptions) -> ExtraRequestOptions:
    """Return `extra` for the pages of a listing after the first.

    A helper that pages through a listing advances the cursor itself. A
    ``cursor`` in ``extra_query`` selects the first page; sent again, it would
    replace every later cursor and fetch that page forever.
    """
    extra_query = extra.get("extra_query")
    if not extra_query or "cursor" not in extra_query:
        return extra
    remaining = {key: value for key, value in extra_query.items() if key != "cursor"}
    return {**extra, "extra_query": remaining}


def merge_body(
    data: Optional[Union[Dict[str, Any], str]],
    extra_body: Optional[Mapping[str, Any]],
) -> Optional[Union[Dict[str, Any], str]]:
    """Return the JSON body to send: `data` with `extra_body` merged over it.

    ``stream`` is never taken from `extra_body`. A request with no body of its
    own sends the extra fields alone.

    Raises:
        TypeError: If `data` is a pre-serialized string, which cannot be merged into.
    """
    if not extra_body:
        return data
    extra = {key: value for key, value in extra_body.items() if key != "stream"}
    if data is None:
        return extra or None
    if not isinstance(data, dict):
        raise TypeError(
            f"Cannot merge extra_body into a request body of type {type(data).__name__}"
        )
    return {**data, **extra}
