"""Local fake API server for offline integration tests.

Serves ``POST /search``, ``POST /findSimilar`` and ``POST /contents`` over real
HTTP on a loopback port, so the SDK's whole transport (URL building, headers,
JSON encoding, status handling, response parsing) runs as it does against the
hosted API.

The server is honest about requests and deliberately simple about results:

* It checks the ``x-api-key`` header and answers a missing or wrong key with
  the API's error shape (``requestId``, ``error``, ``tag``).
* It validates every request body against the documented request schema and
  answers a malformed one with ``400 INVALID_REQUEST_BODY``. It is stricter
  than the hosted API in one way: unknown fields are rejected instead of
  ignored, so a misspelled or mis-cased option fails loudly.
* It honours the contents options a request asks for (text and its
  ``maxCharacters``, highlights, summary, context, livecrawl statuses), and
  returns no contents that were not requested.
* Every query returns the same deterministic fixture documents. Results have
  the shape of real responses, not their relevance or freshness.

Usage::

    with FakeExaApi() as api:
        exa = Exa(api.api_key, base_url=api.url)
"""

from __future__ import annotations

import json
import secrets
import threading
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional
from urllib.parse import urlparse

FAKE_API_KEY = "offline-integration-test-key"

# --------------------------------------------------------------------------
# Errors
# --------------------------------------------------------------------------


class ApiError(Exception):
    """A request the API refuses, rendered as ``{requestId, error, tag}``."""

    def __init__(self, status: int, tag: str, message: str):
        super().__init__(message)
        self.status = status
        self.tag = tag
        self.message = message


def invalid_body(message: str) -> ApiError:
    """The 400 the API returns for a body that fails schema validation."""
    return ApiError(
        400,
        "INVALID_REQUEST_BODY",
        f"Invalid request body | Validation error: {message}",
    )


# --------------------------------------------------------------------------
# Request validation
#
# A validator is a function ``(value, path) -> None`` that raises
# ``invalid_body`` when ``value`` does not match. ``path`` names the field in
# error messages, e.g. ``contents.text.maxCharacters``.
# --------------------------------------------------------------------------

Validator = Callable[[Any, str], None]


def _fail(path: str, expected: str, value: Any) -> ApiError:
    return invalid_body(
        f'Invalid input: expected {expected}, received {type(value).__name__} at "{path}"'
    )


def is_string(value: Any, path: str) -> None:
    if not isinstance(value, str):
        raise _fail(path, "string", value)


def is_nonempty_string(value: Any, path: str) -> None:
    is_string(value, path)
    if not value.strip():
        raise invalid_body(f'Too small: expected a non-empty string at "{path}"')


def is_bool(value: Any, path: str) -> None:
    if not isinstance(value, bool):
        raise _fail(path, "boolean", value)


def is_object(value: Any, path: str) -> None:
    if not isinstance(value, dict):
        raise _fail(path, "object", value)


def is_http_url(value: Any, path: str) -> None:
    is_string(value, path)
    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise invalid_body(f'Invalid URL at "{path}"')


def integer(minimum: Optional[int] = None, maximum: Optional[int] = None) -> Validator:
    """An integer (never a bool) within the inclusive bounds."""

    def check(value: Any, path: str) -> None:
        if isinstance(value, bool) or not isinstance(value, int):
            raise _fail(path, "integer", value)
        if minimum is not None and value < minimum:
            raise invalid_body(
                f'Too small: expected number to be >={minimum} at "{path}"'
            )
        if maximum is not None and value > maximum:
            raise invalid_body(
                f'Too big: expected number to be <={maximum} at "{path}"'
            )

    return check


def one_of(*choices: str) -> Validator:
    def check(value: Any, path: str) -> None:
        if value not in choices:
            options = "|".join(f'"{choice}"' for choice in choices)
            raise invalid_body(f'Invalid option: expected one of {options} at "{path}"')

    return check


def list_of(item: Validator, *, nonempty: bool = False) -> Validator:
    def check(value: Any, path: str) -> None:
        if not isinstance(value, list):
            raise _fail(path, "array", value)
        if nonempty and not value:
            raise invalid_body(f'Too small: expected a non-empty array at "{path}"')
        for index, element in enumerate(value):
            item(element, f"{path}.{index}")

    return check


def any_of(*validators: Validator) -> Validator:
    """Accepts a value any one of ``validators`` accepts; reports the last failure."""

    def check(value: Any, path: str) -> None:
        failure: Optional[ApiError] = None
        for validator in validators:
            try:
                validator(value, path)
                return
            except ApiError as error:
                failure = error
        assert failure is not None
        raise failure

    return check


def obj(fields: Mapping[str, Validator], required: Iterable[str] = ()) -> Validator:
    """An object with only the given fields, each matching its validator."""

    def check(value: Any, path: str) -> None:
        is_object(value, path or "body")
        for name in required:
            if name not in value:
                raise invalid_body(
                    f'Invalid input: expected value, received undefined at "{_join(path, name)}"'
                )
        for name, field_value in value.items():
            if name not in fields:
                raise invalid_body(f'Unrecognized key: "{name}" at "{path or "body"}"')
            fields[name](field_value, _join(path, name))

    return check


def _join(path: str, name: str) -> str:
    return f"{path}.{name}" if path else name


positive_int = integer(minimum=1)
non_negative_int = integer(minimum=0)
string_list = list_of(is_string)

SECTION = one_of(
    "unspecified",
    "header",
    "navigation",
    "banner",
    "body",
    "sidebar",
    "footer",
    "metadata",
)
LIVECRAWL = one_of("never", "fallback", "always", "auto", "preferred")
SEARCH_TYPE = one_of(
    "neural",
    "keyword",
    "auto",
    "hybrid",
    "fast",
    "instant",
    "deep-lite",
    "deep",
    "deep-reasoning",
)
CATEGORY = one_of(
    "company", "news", "publication", "personal site", "financial report", "people"
)

TEXT_OPTIONS = any_of(
    is_bool,
    obj(
        {
            "maxCharacters": positive_int,
            "includeHtmlTags": is_bool,
            "verbosity": one_of("compact", "standard", "full"),
            "includeSections": list_of(SECTION),
            "excludeSections": list_of(SECTION),
        }
    ),
)
HIGHLIGHTS_OPTIONS = any_of(
    is_bool,
    obj(
        {
            "query": is_string,
            "maxCharacters": positive_int,
            "dynamic": is_bool,
            "numSentences": positive_int,
            "highlightsPerUrl": positive_int,
        }
    ),
)
SUMMARY_OPTIONS = any_of(is_bool, obj({"query": is_string, "schema": is_object}))
CONTEXT_OPTIONS = any_of(is_bool, obj({"maxCharacters": positive_int}))

CONTENTS_FIELDS: Dict[str, Validator] = {
    "text": TEXT_OPTIONS,
    "highlights": HIGHLIGHTS_OPTIONS,
    "summary": SUMMARY_OPTIONS,
    "context": CONTEXT_OPTIONS,
    "metadata": any_of(is_bool, is_object),
    "livecrawl": LIVECRAWL,
    "livecrawlTimeout": non_negative_int,
    "maxAgeHours": integer(minimum=-1),
    "snapshotAsOf": is_string,
    "filterEmptyResults": is_bool,
    "subpages": non_negative_int,
    "subpageTarget": any_of(is_string, string_list),
    "extras": obj({"links": non_negative_int, "imageLinks": non_negative_int}),
}

# The API requires `contents` to be an object: `contents: false` is refused,
# so a client must omit the field to ask for no contents.
CONTENTS_OPTIONS = obj(CONTENTS_FIELDS)

FILTER_FIELDS: Dict[str, Validator] = {
    "numResults": integer(minimum=1, maximum=100),
    "includeDomains": string_list,
    "excludeDomains": string_list,
    "includeText": string_list,
    "excludeText": string_list,
    "startCrawlDate": is_string,
    "endCrawlDate": is_string,
    "startPublishedDate": is_string,
    "endPublishedDate": is_string,
    "category": CATEGORY,
    "flags": string_list,
    "userLocation": is_string,
    "contents": CONTENTS_OPTIONS,
}

SEARCH_REQUEST = obj(
    {
        "query": is_nonempty_string,
        "type": SEARCH_TYPE,
        "additionalQueries": string_list,
        "useAutoprompt": is_bool,
        "moderation": is_bool,
        "systemPrompt": is_string,
        "outputSchema": is_object,
        **FILTER_FIELDS,
    },
    required=["query"],
)
FIND_SIMILAR_REQUEST = obj(
    {"url": is_http_url, "excludeSourceDomain": is_bool, **FILTER_FIELDS},
    required=["url"],
)
CONTENTS_REQUEST = obj(
    {
        "urls": list_of(is_nonempty_string, nonempty=True),
        "ids": list_of(is_nonempty_string, nonempty=True),
        "flags": string_list,
        **CONTENTS_FIELDS,
    }
)


def check_freshness_options(options: Mapping[str, Any]) -> None:
    """The API refuses `livecrawl` with `maxAgeHours` (livecrawl is deprecated in its favour)."""
    if "livecrawl" in options and "maxAgeHours" in options:
        raise ApiError(
            400,
            "INVALID_REQUEST",
            "Cannot set both 'livecrawl' and 'maxAgeHours'. Use 'maxAgeHours' instead (livecrawl is deprecated).",
        )


# --------------------------------------------------------------------------
# Fixture documents
# --------------------------------------------------------------------------

_SENTENCES = (
    "This fixture document stands in for a crawled web page.",
    "Its text is long enough to exercise character limits on returned contents.",
    "Every sentence is deterministic, so test runs are reproducible.",
    "Highlights and summaries are drawn from these same sentences.",
    "Nothing here depends on the network or on live data.",
)


@dataclass(frozen=True)
class Document:
    """One fixture web page."""

    url: str
    title: str
    author: str
    published_date: str
    text: str

    @property
    def host(self) -> str:
        return urlparse(self.url).netloc

    def sentences(self) -> List[str]:
        return [sentence for sentence in self.text.split("\n") if sentence]


def make_document(url: str, title: str, index: int) -> Document:
    """A deterministic document of roughly 12,000 characters."""
    lines = [title]
    paragraph = 0
    while sum(len(line) + 1 for line in lines) < 12_000:
        paragraph += 1
        sentence = _SENTENCES[paragraph % len(_SENTENCES)]
        lines.append(f"Paragraph {paragraph} of document {index}. {sentence}")
    return Document(
        url=url,
        title=title,
        author=f"Fixture Author {index}",
        published_date=f"2024-01-{index:02d}T00:00:00.000Z",
        text="\n".join(lines),
    )


DOCUMENTS = tuple(
    make_document(
        f"https://site-{index}.example.com/articles/{index}",
        f"Fixture Document {index}",
        index,
    )
    for index in range(1, 13)
)


def document_for_url(url: str) -> Document:
    """The fixture document at ``url``, or a deterministic one made for it."""
    for document in DOCUMENTS:
        if document.url == url:
            return document
    return make_document(url, f"Fixture page for {urlparse(url).netloc or url}", 0)


# --------------------------------------------------------------------------
# Response rendering
# --------------------------------------------------------------------------


def _limit(value: str, options: Any) -> str:
    """Truncates ``value`` to ``options.maxCharacters`` when an object sets it."""
    if isinstance(options, dict) and "maxCharacters" in options:
        return value[: options["maxCharacters"]]
    return value


def render_highlights(document: Document, options: Any) -> List[str]:
    settings = options if isinstance(options, dict) else {}
    count = settings.get("highlightsPerUrl", 1)
    width = settings.get("numSentences", 2)
    sentences = document.sentences()[1:]
    highlights = [
        " ".join(sentences[start : start + width])
        for start in range(0, count * width, width)
    ]
    return [_limit(highlight, settings) for highlight in highlights]


def render_summary(document: Document, options: Any) -> str:
    query = options.get("query") if isinstance(options, dict) else None
    summary = f"Summary of {document.title}: a deterministic fixture page used by offline tests."
    if query:
        summary += f" It answers the question: {query}"
    return summary


def render_work_history(index: int) -> List[dict]:
    """A current role (open-ended, ``to`` is null) and a finished one."""
    return [
        {
            "title": "Software Engineer",
            "location": "Example City",
            "dates": {"from": f"2024-{index:02d}-01", "to": None},
            "company": {
                "id": "https://example.com/company/current",
                "name": "Current Fixture Company",
            },
        },
        {
            "title": "Software Engineer Intern",
            "location": None,
            "dates": {"from": "2022-06-01", "to": "2022-09-01"},
            "company": {"id": None, "name": "Previous Fixture Company"},
        },
    ]


def render_entities(
    document: Document, index: int, category: Optional[str]
) -> Optional[List[dict]]:
    """Company or person entities, which the API returns only for those categories."""
    if category == "company":
        return [
            {
                "id": document.url,
                "type": "company",
                "version": 1,
                "properties": {
                    "name": f"Fixture Company {index}",
                    "foundedYear": 2000 + index,
                    "description": "A fixture company used by offline tests.",
                    "workforce": {"total": 10 * index},
                    "headquarters": {
                        "address": f"{index} Example Street",
                        "city": "Example City",
                        "postalCode": None,
                        "country": "United States",
                    },
                    "financials": {
                        "revenueAnnual": None,
                        "fundingTotal": 1_000_000 * index,
                        "fundingLatestRound": {
                            "name": "Seed",
                            "date": "2024-01-01",
                            "amount": 1_000_000,
                        },
                    },
                    "webTraffic": {"visitsMonthly": 1000 * index},
                },
            }
        ]
    if category == "people":
        return [
            {
                "id": document.url,
                "type": "person",
                "version": 1,
                "properties": {
                    "name": f"Fixture Person {index}",
                    "location": "Example City",
                    "workHistory": render_work_history(index),
                },
            }
        ]
    return None


def render_result(
    document: Document,
    contents: Mapping[str, Any],
    *,
    index: int,
    score: Optional[float] = None,
    category: Optional[str] = None,
) -> dict:
    """One result with exactly the contents ``contents`` asks for."""
    result: Dict[str, Any] = {
        "id": document.url,
        "url": document.url,
        "title": document.title,
        "author": document.author,
        "publishedDate": document.published_date,
    }
    if score is not None:
        result["score"] = score
    if contents.get("text"):
        result["text"] = _limit(document.text, contents["text"])
    if contents.get("highlights"):
        highlights = render_highlights(document, contents["highlights"])
        result["highlights"] = highlights
        result["highlightScores"] = [0.9 - 0.1 * i for i in range(len(highlights))]
    if contents.get("summary"):
        result["summary"] = render_summary(document, contents["summary"])
    entities = render_entities(document, index, category)
    if entities is not None:
        result["entities"] = entities
    return result


def render_context(results: List[dict], options: Any) -> str:
    """The deprecated combined context string built from the results."""
    blocks = []
    for result in results:
        block = f"Title: {result['title']}\nURL: {result['url']}\n"
        if "text" in result:
            block += f"{result['text']}\n"
        blocks.append(block)
    return _limit("\n".join(blocks), options)


def search_response(
    documents: List[Document],
    request: Mapping[str, Any],
    contents: Mapping[str, Any],
    *,
    search_type: Optional[str],
) -> dict:
    """The response body shared by `/search` and `/findSimilar`."""
    results = [
        render_result(
            document,
            contents,
            index=index,
            score=round(0.99 - 0.01 * index, 2),
            category=request.get("category"),
        )
        for index, document in enumerate(documents, start=1)
    ]
    response: Dict[str, Any] = {
        "requestId": secrets.token_hex(16),
        "results": results,
        "searchTime": 1.0,
        "costDollars": {"total": 0.005},
    }
    if search_type is not None:
        response["resolvedSearchType"] = (
            "neural" if search_type == "auto" else search_type
        )
    if contents.get("context"):
        response["context"] = render_context(results, contents["context"])
    return response


# --------------------------------------------------------------------------
# Endpoints: each takes a parsed body and returns a response body.
# --------------------------------------------------------------------------


def handle_search(body: Mapping[str, Any]) -> dict:
    SEARCH_REQUEST(body, "")
    contents = body.get("contents", {})
    check_freshness_options(contents)
    documents = list(DOCUMENTS[: body.get("numResults", 10)])
    return search_response(
        documents, body, contents, search_type=body.get("type", "auto")
    )


def handle_find_similar(body: Mapping[str, Any]) -> dict:
    FIND_SIMILAR_REQUEST(body, "")
    contents = body.get("contents", {})
    check_freshness_options(contents)
    source_host = urlparse(body["url"]).netloc
    candidates = [
        document
        for document in DOCUMENTS
        if document.url != body["url"]
        and not (body.get("excludeSourceDomain") and document.host == source_host)
    ]
    documents = candidates[: body.get("numResults", 10)]
    return search_response(documents, body, contents, search_type=None)


def handle_contents(body: Mapping[str, Any]) -> dict:
    CONTENTS_REQUEST(body, "")
    check_freshness_options(body)
    urls = body.get("urls", body.get("ids"))
    if urls is None:
        raise invalid_body(
            'Invalid input: expected array, received undefined at "urls"'
        )
    contents = dict(body)
    # Without any contents option the endpoint returns full text.
    if not any(key in body for key in ("text", "highlights", "summary")):
        contents["text"] = True
    crawled = (
        body.get("livecrawl") in ("always", "preferred") or body.get("maxAgeHours") == 0
    )
    results = [
        render_result(document_for_url(url), contents, index=index)
        for index, url in enumerate(urls, start=1)
    ]
    response: Dict[str, Any] = {
        "requestId": secrets.token_hex(16),
        "results": results,
        "statuses": [
            {
                "id": url,
                "status": "success",
                "source": "crawled" if crawled else "cached",
            }
            for url in urls
        ],
        "costDollars": {"total": 0.001 * len(urls)},
    }
    if contents.get("context"):
        response["context"] = render_context(results, contents["context"])
    return response


ROUTES: Dict[str, Callable[[Mapping[str, Any]], dict]] = {
    "/search": handle_search,
    "/findSimilar": handle_find_similar,
    "/contents": handle_contents,
}


# --------------------------------------------------------------------------
# HTTP server
# --------------------------------------------------------------------------


def authenticate(headers: Mapping[str, str], api_key: str) -> None:
    """Accepts ``x-api-key: <key>`` or ``Authorization: Bearer <key>``."""
    presented = headers.get("x-api-key")
    authorization = headers.get("authorization", "")
    if presented is None and authorization.lower().startswith("bearer "):
        presented = authorization[len("bearer ") :]
    if not presented:
        # The hosted API answers a keyless request with a payment-required
        # challenge; the fake keeps its status, tag and message.
        raise ApiError(
            402, "X402_PAYMENT_REQUIRED", "Payment required to access this resource"
        )
    if not secrets.compare_digest(presented, api_key):
        raise ApiError(
            401,
            "INVALID_API_KEY",
            "Invalid API key. Provide a valid key using 'Authorization: Bearer <key>' or 'x-api-key: <key>'.",
        )


def dispatch(
    method: str, path: str, headers: Mapping[str, str], raw_body: bytes, api_key: str
) -> dict:
    """Routes one request and returns its response body, or raises ``ApiError``."""
    route = ROUTES.get(urlparse(path).path)
    if method != "POST" or route is None:
        raise ApiError(404, "NOT_FOUND", "Not found")
    authenticate(headers, api_key)
    try:
        body = json.loads(raw_body or b"null")
    except json.JSONDecodeError as error:
        raise invalid_body(f"Malformed JSON: {error.msg}") from error
    return route(body)


class FakeExaApi:
    """The fake API server, running on a background thread until stopped."""

    def __init__(
        self, api_key: str = FAKE_API_KEY, host: str = "127.0.0.1", port: int = 0
    ):
        self.api_key = api_key
        self._address = (host, port)
        self._server: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    @property
    def url(self) -> str:
        """The base URL to pass to the client, e.g. ``http://127.0.0.1:54321``."""
        if self._server is None:
            raise RuntimeError("FakeExaApi is not running")
        host, port = self._server.server_address[:2]
        return f"http://{host}:{port}"

    def start(self) -> "FakeExaApi":
        self._server = ThreadingHTTPServer(self._address, _make_handler(self.api_key))
        self._server.daemon_threads = True
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self._thread is not None:
            self._thread.join()
            self._thread = None

    def __enter__(self) -> "FakeExaApi":
        return self.start()

    def __exit__(self, *_exc: object) -> None:
        self.stop()


def _make_handler(api_key: str) -> type:
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def _handle(self) -> None:
            length = int(self.headers.get("Content-Length") or 0)
            raw_body = self.rfile.read(length) if length else b""
            headers = {name.lower(): value for name, value in self.headers.items()}
            try:
                status, payload = (
                    200,
                    dispatch(self.command, self.path, headers, raw_body, api_key),
                )
            except ApiError as error:
                status = error.status
                payload = {
                    "requestId": secrets.token_hex(16),
                    "error": error.message,
                    "tag": error.tag,
                }
            encoded = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = _handle

        def log_message(self, format: str, *args: Any) -> None:
            """Silences the default per-request stderr log."""

    return Handler
