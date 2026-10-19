"""A successful response whose body is not JSON raises an error naming the status and body."""

import httpx
import pytest
import requests

from exa_py import AsyncExa, Exa, api as exa_api

API_KEY = "test-key"
HTML_PAGE = "<!DOCTYPE html>\n<html>\n  <title>Bad gateway</title>\n</html>"
HTML_SNIPPET = "<!DOCTYPE html> <html> <title>Bad gateway</title> </html>"


def _requests_response(status_code: int, body: str) -> requests.Response:
    response = requests.Response()
    response.status_code = status_code
    response._content = body.encode("utf-8")
    response.encoding = "utf-8"
    return response


def _patch_post(monkeypatch, status_code: int, body: str) -> None:
    monkeypatch.setattr(
        exa_api.requests,
        "post",
        lambda *args, **kwargs: _requests_response(status_code, body),
    )


def _async_exa(status_code: int, body: str) -> AsyncExa:
    exa = AsyncExa(API_KEY)
    exa._client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(status_code, text=body)
        )
    )
    return exa


def test_sync_html_success_body_names_status_and_body(monkeypatch):
    _patch_post(monkeypatch, 200, HTML_PAGE)

    with pytest.raises(ValueError) as exc:
        Exa(API_KEY).search("test")

    assert str(exc.value) == (
        "Expected a JSON response but received a non-JSON body (status 200): "
        + HTML_SNIPPET
    )
    assert isinstance(exc.value.__cause__, ValueError)


def test_sync_empty_success_body_names_status(monkeypatch):
    _patch_post(monkeypatch, 200, "")

    with pytest.raises(ValueError) as exc:
        Exa(API_KEY).request("/search", {"query": "test"})

    assert str(exc.value) == (
        "Expected a JSON response but received an empty body (status 200)."
    )


def test_sync_long_body_is_truncated_to_500_characters(monkeypatch):
    _patch_post(monkeypatch, 200, "x" * 600)

    with pytest.raises(ValueError) as exc:
        Exa(API_KEY).request("/search", {"query": "test"})

    assert str(exc.value).endswith(": " + "x" * 500 + "\u2026")


def test_sync_json_success_body_is_returned(monkeypatch):
    _patch_post(monkeypatch, 200, '{"results": []}')

    assert Exa(API_KEY).request("/search", {"query": "test"}) == {"results": []}


def test_sync_error_status_keeps_its_message(monkeypatch):
    _patch_post(monkeypatch, 502, HTML_PAGE)

    with pytest.raises(ValueError, match="Request failed with status code 502"):
        Exa(API_KEY).request("/search", {"query": "test"})


@pytest.mark.asyncio
async def test_async_html_success_body_names_status_and_body():
    exa = _async_exa(200, HTML_PAGE)
    try:
        with pytest.raises(ValueError) as exc:
            await exa.search("test")
    finally:
        await exa.aclose()

    assert str(exc.value) == (
        "Expected a JSON response but received a non-JSON body (status 200): "
        + HTML_SNIPPET
    )
    assert isinstance(exc.value.__cause__, ValueError)


@pytest.mark.asyncio
async def test_async_empty_success_body_names_status():
    exa = _async_exa(200, "")
    try:
        with pytest.raises(ValueError) as exc:
            await exa.async_request("/search", {"query": "test"})
    finally:
        await exa.aclose()

    assert str(exc.value) == (
        "Expected a JSON response but received an empty body (status 200)."
    )


@pytest.mark.asyncio
async def test_async_json_success_body_is_returned():
    exa = _async_exa(200, '{"results": []}')
    try:
        assert await exa.async_request("/search", {"query": "test"}) == {"results": []}
    finally:
        await exa.aclose()
