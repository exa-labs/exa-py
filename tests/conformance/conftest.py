"""Offline HTTP interception helpers for SDK conformance tests."""

from __future__ import annotations

import io
import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from urllib.parse import urlsplit

import httpx
import pytest
import requests
from pathlib import Path
from requests import Response
from requests.adapters import HTTPAdapter
from urllib3 import HTTPResponse


@dataclass
class RecordedRequest:
    mode: str
    method: str
    url: str
    headers: Dict[str, str]
    body: Optional[str]
    outcome: str = "ok"

    def as_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "method": self.method,
            "url": self.url,
            "headers": self.headers,
            "body": self.body,
            "outcome": self.outcome,
        }


class OfflineTransport:
    """Capture requests and return deterministic JSON or SSE responses."""

    def __init__(self) -> None:
        self.requests: List[RecordedRequest] = []
        self.streaming = False
        self.payload: Dict[str, Any] = {}
        self.response_fixtures: Dict[str, Dict[str, Any]] = {}

    def response_for(self, method: str, url: str) -> Dict[str, Any]:
        path = urlsplit(url).path
        for endpoint, payload in self.response_fixtures.items():
            expected_method, template = endpoint.split(" ", 1)
            if expected_method == method and path_matches_template(url, template):
                return payload
        raise KeyError(f"missing response fixture for {method} {path}")

    def _headers(self, headers: Any) -> Dict[str, str]:
        result = {str(k).lower(): str(v) for k, v in headers.items()}
        if "x-api-key" in result:
            result["x-api-key"] = "<dummy-api-key>"
        if "user-agent" in result:
            result["user-agent"] = "<exa-py/version>"
        return dict(sorted(result.items()))

    def _capture(
        self, method: str, url: str, headers: Any, body: Any, mode: str
    ) -> None:
        if body is None:
            body_text = None
        elif isinstance(body, bytes):
            body_text = body.decode("utf-8")
        else:
            body_text = str(body)
        if body_text == "":
            body_text = None
        self.requests.append(
            RecordedRequest(
                mode=mode,
                method=method.upper(),
                url=url,
                headers=self._headers(headers),
                body=body_text,
            )
        )

    def send(self, request: requests.PreparedRequest, **kwargs: Any) -> Response:
        """Implement the lowest requests transport boundary."""
        self._capture(
            request.method or "GET",
            request.url,
            request.headers,
            request.body,
            "sync",
        )
        response = Response()
        response.status_code = 200
        response.url = request.url
        response.request = request
        response.headers["Content-Type"] = (
            "text/event-stream" if self.streaming else "application/json"
        )
        if self.streaming:
            payload = (
                b'data: {"content":"hello"}\n\n'
                b'data: {"citations":[]}\n\n'
                b"data: [DONE]\n\n"
            )
            response.raw = HTTPResponse(
                body=io.BytesIO(payload), preload_content=False
            )
        else:
            response._content = json.dumps(
                self.response_for(request.method or "GET", request.url)
            ).encode()
        return response

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        """Implement the lowest httpx async transport boundary."""
        self._capture(
            request.method,
            str(request.url),
            request.headers,
            request.content,
            "async",
        )
        if self.streaming:
            payload = (
                b'data: {"content":"hello"}\n\n'
                b'data: {"citations":[]}\n\n'
                b"data: [DONE]\n\n"
            )
            return httpx.Response(
                200,
                headers={"content-type": "text/event-stream"},
                stream=httpx.ByteStream(payload),
                request=request,
            )
        return httpx.Response(
            200,
            json=self.response_for(request.method, str(request.url)),
            request=request,
        )


@pytest.fixture
def offline_transport(monkeypatch: pytest.MonkeyPatch) -> OfflineTransport:
    """Patch both SDK HTTP boundaries without replacing SDK methods."""
    transport = OfflineTransport()
    fixture_path = Path(__file__).parent / "fixtures" / "responses.json"
    transport.response_fixtures = {
        item["endpoint"]: item["payload"] for item in read_json_lines(fixture_path)
    }
    monkeypatch.setattr(HTTPAdapter, "send", transport.send)
    monkeypatch.setattr(
        httpx.AsyncHTTPTransport,
        "handle_async_request",
        transport.handle_async_request,
    )
    return transport


def write_or_compare(path: Any, value: Any) -> None:
    """Write a golden in record mode or compare it with the committed file."""
    rendered = "".join(
        json.dumps(item, separators=(",", ":"), sort_keys=True) + "\n"
        for item in value
    )
    if os.environ.get("EXA_CONFORMANCE_RECORD") == "1":
        path.write_text(rendered)
        return
    assert path.read_text() == rendered


def read_json_lines(path: Any) -> list[Any]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def path_matches_template(url: str, template: str) -> bool:
    """Check a captured URL path against an inventory template."""
    actual = urlsplit(url).path
    pattern = template.replace("{", "<").replace("}", ">")
    parts = pattern.split("/")
    actual_parts = actual.split("/")
    if len(parts) != len(actual_parts):
        return False
    return all(
        expected.startswith("<") or expected == actual_part
        for expected, actual_part in zip(parts, actual_parts)
    )
