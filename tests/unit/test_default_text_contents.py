"""The default text request is added only when the caller picked no content type."""

from unittest.mock import AsyncMock, patch

import pytest

from exa_py import AsyncExa, Exa

API_KEY = "test-key"
URL = "https://example.com/article"
RESPONSE = {"results": [], "statuses": []}

CALLS = {
    "get_contents": lambda exa, **kwargs: exa.get_contents([URL], **kwargs),
    "search_and_contents": lambda exa, **kwargs: exa.search_and_contents(
        "query", **kwargs
    ),
    "find_similar_and_contents": lambda exa, **kwargs: exa.find_similar_and_contents(
        URL, **kwargs
    ),
}

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


def _contents_options(body):
    # get_contents sends the content options at the top level, the other two under "contents"
    return body.get("contents", body)


def _sent_sync(method, **kwargs):
    exa = Exa(API_KEY)
    with patch.object(exa, "request", return_value=RESPONSE) as request:
        CALLS[method](exa, **kwargs)
    return _contents_options(request.call_args.args[1])


async def _sent_async(method, **kwargs):
    exa = AsyncExa(API_KEY)
    request = AsyncMock(return_value=RESPONSE)
    with patch.object(exa, "async_request", new=request):
        await CALLS[method](exa, **kwargs)
    return _contents_options(request.call_args.args[1])


@pytest.mark.parametrize("method", CALLS)
def test_highlights_only_does_not_also_request_text(method):
    sent = _sent_sync(method, highlights=True)

    assert sent["highlights"] is True
    assert "text" not in sent


@pytest.mark.asyncio
@pytest.mark.parametrize("method", CALLS)
async def test_async_highlights_only_does_not_also_request_text(method):
    sent = await _sent_async(method, highlights=True)

    assert sent["highlights"] is True
    assert "text" not in sent


@pytest.mark.parametrize("method", CALLS)
def test_no_content_type_still_defaults_to_text(method):
    sent = _sent_sync(method)

    assert sent["text"] == {"maxCharacters": 10000}


@pytest.mark.asyncio
@pytest.mark.parametrize("method", CALLS)
async def test_async_no_content_type_still_defaults_to_text(method):
    sent = await _sent_async(method)

    assert sent["text"] == {"maxCharacters": 10000}


@pytest.mark.parametrize("method", CALLS)
def test_text_and_highlights_are_both_sent_when_both_are_asked_for(method):
    sent = _sent_sync(method, text=True, highlights=True)

    assert sent["text"] is True
    assert sent["highlights"] is True


@pytest.mark.parametrize("method", CALLS)
def test_summary_only_does_not_also_request_text(method):
    sent = _sent_sync(method, summary=True)

    assert sent["summary"] is True
    assert "text" not in sent
