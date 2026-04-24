import os
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from exa_py import Exa, AsyncExa, api as exa_api

API_KEY = os.getenv("EXA_API_KEY", "test-key")


def _have_real_key() -> bool:
    return API_KEY != "test-key" and len(API_KEY) > 10


class _FakeStreamResponse:
    def __init__(self, lines: list[str], status_code: int = 200):
        self._lines = lines
        self.status_code = status_code
        self.text = ""

    def iter_lines(self):
        for line in self._lines:
            yield line.encode("utf-8")

    def close(self):
        return None


class _FakeAsyncStreamResponse:
    def __init__(self, lines: list[str], status_code: int = 200):
        self._lines = lines
        self.status_code = status_code
        self.text = ""

    async def aiter_lines(self):
        for line in self._lines:
            yield line

    def close(self):
        return None


########################################
# Offline unit tests (no network)
########################################


def test_contentstatus_parsing_offline():
    payload_status = {"id": "u", "status": "success", "source": "cached"}
    cs = exa_api.ContentStatus(**payload_status)
    assert cs.id == "u" and cs.status == "success" and cs.source == "cached"


def test_answerresponse_accepts_dict():
    dummy = exa_api.AnswerResult(id="1", url="u", title="t")
    resp = exa_api.AnswerResponse(answer={"foo": "bar"}, citations=[dummy])
    assert isinstance(resp.answer, dict) and resp.answer["foo"] == "bar"


def test_search_accepts_user_location_offline():
    """Test that search method accepts user_location parameter without error."""
    exa = Exa(API_KEY)
    # Create a mock response
    mock_response = {
        "results": [{"url": "http://example.com", "id": "1", "title": "Test"}],
        "costDollars": {"total": 0.001},
    }

    with patch.object(exa, "request", return_value=mock_response):
        # This should not raise any errors about unknown parameters
        resp = exa.search("test query", user_location="US", num_results=1)
        assert isinstance(resp, exa_api.SearchResponse)


def test_search_accepts_additional_queries_offline():
    """Test that search method accepts additional_queries parameter for deep search.
    
    Deep search always returns context in the response.
    """
    exa = Exa(API_KEY)
    # Create a mock response with context (always returned for deep search)
    mock_response = {
        "results": [
            {"url": "http://example.com", "id": "1", "title": "Deep Search Result"}
        ],
        "context": "Deep search context string",
        "costDollars": {"total": 0.002},
    }

    with patch.object(exa, "request", return_value=mock_response) as mock_request:
        # Test with additional_queries for deep search
        resp = exa.search(
            "machine learning",
            type="deep",
            additional_queries=["ML algorithms", "neural networks", "AI models"],
            num_results=5,
        )
        assert isinstance(resp, exa_api.SearchResponse)
        assert resp.context is not None  # Context always present for deep search
        
        # Verify the request was called with correct camelCase parameters
        call_args = mock_request.call_args
        assert call_args[0][0] == "/search"
        options = call_args[0][1]
        assert "additionalQueries" in options
        assert options["additionalQueries"] == ["ML algorithms", "neural networks", "AI models"]
        assert options["type"] == "deep"


def test_search_accepts_instant_type_offline():
    """Test that search method accepts instant search type and forwards it as-is."""
    exa = Exa(API_KEY)
    mock_response = {
        "results": [
            {
                "url": "http://example.com",
                "id": "1",
                "title": "Instant Search Result",
            }
        ],
        "costDollars": {"total": 0.001},
    }

    with patch.object(exa, "request", return_value=mock_response) as mock_request:
        resp = exa.search(
            "instant query",
            type="instant",
            num_results=3,
        )
        assert isinstance(resp, exa_api.SearchResponse)

        call_args = mock_request.call_args
        assert call_args[0][0] == "/search"
        options = call_args[0][1]
        assert options["type"] == "instant"


def test_search_accepts_deep_reasoning_params_offline():
    """Test deep-reasoning search accepts output_schema params."""
    exa = Exa(API_KEY)
    mock_response = {
        "results": [
            {"url": "http://example.com", "id": "1", "title": "Deep Search Result"}
        ],
        "output": {
            "content": {"answer_text": "Deep search synthesis"},
            "grounding": [
                {
                    "field": "answer_text",
                    "citations": [
                        {"url": "http://example.com", "title": "Deep Search Result"}
                    ],
                    "confidence": "high",
                }
            ],
        },
        "costDollars": {"total": 0.002},
    }

    output_schema = {
        "type": "object",
        "properties": {
            "answer_text": {"type": "string"},
        },
        "required": ["answer_text"],
    }

    with patch.object(exa, "request", return_value=mock_response) as mock_request:
        resp = exa.search(
            "machine learning",
            type="deep-reasoning",
            output_schema=output_schema,
            num_results=5,
        )
        assert isinstance(resp, exa_api.SearchResponse)
        assert resp.output is not None
        assert resp.output.content == {"answer_text": "Deep search synthesis"}
        assert len(resp.output.grounding) == 1
        assert resp.output.grounding[0].field == "answer_text"
        assert resp.output.grounding[0].confidence == "high"
        assert len(resp.output.grounding[0].citations) == 1
        assert resp.output.grounding[0].citations[0].url == "http://example.com"
        assert (
            resp.output.grounding[0].citations[0].title == "Deep Search Result"
        )

        call_args = mock_request.call_args
        assert call_args[0][0] == "/search"
        options = call_args[0][1]
        assert options["type"] == "deep-reasoning"
        assert "outputSchema" in options
        assert options["outputSchema"]["properties"]["answer_text"]["type"] == "string"
        assert "answerText" not in options["outputSchema"]["properties"]


def test_search_accepts_output_schema_on_fast_search_offline():
    """Test non-deep search accepts output_schema and returns parsed output."""
    exa = Exa(API_KEY)
    mock_response = {
        "results": [
            {"url": "http://example.com", "id": "1", "title": "Fast Search Result"}
        ],
        "output": {
            "content": {"summary": "Fast search synthesis"},
            "grounding": [
                {
                    "field": "summary",
                    "citations": [
                        {"url": "http://example.com", "title": "Fast Search Result"}
                    ],
                    "confidence": "high",
                }
            ],
        },
        "costDollars": {"total": 0.002},
    }

    output_schema = {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
        },
        "required": ["summary"],
    }

    with patch.object(exa, "request", return_value=mock_response) as mock_request:
        resp = exa.search(
            "machine learning",
            type="fast",
            output_schema=output_schema,
            num_results=5,
        )
        assert isinstance(resp, exa_api.SearchResponse)
        assert resp.output is not None
        assert resp.output.content == {"summary": "Fast search synthesis"}
        assert resp.output.grounding[0].field == "summary"

        call_args = mock_request.call_args
        assert call_args[0][0] == "/search"
        options = call_args[0][1]
        assert options["type"] == "fast"
        assert options["outputSchema"]["properties"]["summary"]["type"] == "string"


def test_search_accepts_system_prompt_on_auto_search_offline():
    """Test non-deep search accepts system_prompt and forwards it as camelCase."""
    exa = Exa(API_KEY)
    mock_response = {
        "results": [
            {"url": "http://example.com", "id": "1", "title": "Auto Search Result"}
        ],
        "costDollars": {"total": 0.002},
    }

    with patch.object(exa, "request", return_value=mock_response) as mock_request:
        resp = exa.search(
            "compare recent model launches",
            type="auto",
            system_prompt="Prefer official sources and avoid duplicate results",
        )
        assert isinstance(resp, exa_api.SearchResponse)

        call_args = mock_request.call_args
        assert call_args[0][0] == "/search"
        options = call_args[0][1]
        assert options["type"] == "auto"
        assert (
            options["systemPrompt"]
            == "Prefer official sources and avoid duplicate results"
        )


def test_search_accepts_deep_lite_additional_queries_offline():
    """Test deep-lite search accepts additional_queries and forwards them."""
    exa = Exa(API_KEY)
    mock_response = {
        "results": [
            {"url": "http://example.com", "id": "1", "title": "Deep Lite Result"}
        ],
        "costDollars": {"total": 0.002},
    }

    with patch.object(exa, "request", return_value=mock_response) as mock_request:
        resp = exa.search(
            "machine learning",
            type="deep-lite",
            additional_queries=["ML algorithms", "neural networks", "AI models"],
            num_results=5,
        )
        assert isinstance(resp, exa_api.SearchResponse)

        call_args = mock_request.call_args
        assert call_args[0][0] == "/search"
        options = call_args[0][1]
        assert options["type"] == "deep-lite"
        assert "additionalQueries" in options
        assert options["additionalQueries"] == [
            "ML algorithms",
            "neural networks",
            "AI models",
        ]


def test_search_rejects_stream_flag_offline():
    """Test search(stream=True) points callers to stream_search."""
    exa = Exa(API_KEY)

    with pytest.raises(ValueError, match="Please use `stream_search"):
        exa.search("streaming query", stream=True)


def test_stream_search_streams_openai_style_chunks_offline():
    """Test stream_search forwards stream=true and yields parsed chunks."""
    exa = Exa(API_KEY)
    mock_stream_response = _FakeStreamResponse(
        [
            'data: {"choices":[{"delta":{"content":"Hello"}}]}',
            'data: {"citations":[{"id":"1","url":"http://example.com","title":"Example"}]}',
        ]
    )

    with patch.object(exa, "request", return_value=mock_stream_response) as mock_request:
        stream = exa.stream_search(
            "streaming query",
            type="auto",
            system_prompt="Be concise",
            output_schema={"type": "text", "description": "Short answer"},
        )
        chunks = list(stream)

        assert len(chunks) == 2
        assert chunks[0].content == "Hello"
        assert chunks[1].citations is not None
        assert chunks[1].citations[0].url == "http://example.com"

        call_args = mock_request.call_args
        assert call_args[0][0] == "/search"
        options = call_args[0][1]
        assert options["stream"] is True
        assert options["type"] == "auto"
        assert options["systemPrompt"] == "Be concise"
        assert options["outputSchema"]["type"] == "text"


@pytest.mark.asyncio
async def test_async_search_accepts_deepv3_params_offline():
    """Test async deep-reasoning search accepts output_schema params."""
    ax = AsyncExa(API_KEY)
    mock_response = {
        "results": [{"url": "http://example.com", "id": "1", "title": "Async Result"}],
        "costDollars": {"total": 0.001},
    }

    output_schema = {
        "type": "object",
        "properties": {
            "answer_text": {"type": "string"},
        },
    }

    with patch.object(
        ax, "async_request", new=AsyncMock(return_value=mock_response)
    ) as mock_async_request:
        resp = await ax.search(
            "async deep query",
            type="deep-reasoning",
            output_schema=output_schema,
        )
        assert isinstance(resp, exa_api.SearchResponse)

        call_args = mock_async_request.call_args
        assert call_args[0][0] == "/search"
        options = call_args[0][1]
        assert options["type"] == "deep-reasoning"
        assert options["outputSchema"]["properties"]["answer_text"]["type"] == "string"
        assert "answerText" not in options["outputSchema"]["properties"]


@pytest.mark.asyncio
async def test_async_search_accepts_output_schema_on_fast_search_offline():
    """Test async non-deep search accepts output_schema and returns parsed output."""
    ax = AsyncExa(API_KEY)
    mock_response = {
        "results": [{"url": "http://example.com", "id": "1", "title": "Async Result"}],
        "output": {
            "content": {"summary": "Async fast synthesis"},
            "grounding": [
                {
                    "field": "summary",
                    "citations": [{"url": "http://example.com", "title": "Async Result"}],
                    "confidence": "high",
                }
            ],
        },
        "costDollars": {"total": 0.001},
    }

    output_schema = {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
        },
    }

    with patch.object(
        ax, "async_request", new=AsyncMock(return_value=mock_response)
    ) as mock_async_request:
        resp = await ax.search(
            "async search query",
            type="fast",
            output_schema=output_schema,
        )
        assert isinstance(resp, exa_api.SearchResponse)
        assert resp.output is not None
        assert resp.output.content == {"summary": "Async fast synthesis"}

        call_args = mock_async_request.call_args
        assert call_args[0][0] == "/search"
        options = call_args[0][1]
        assert options["type"] == "fast"
        assert options["outputSchema"]["properties"]["summary"]["type"] == "string"


@pytest.mark.asyncio
async def test_async_search_accepts_system_prompt_on_auto_search_offline():
    """Test async non-deep search accepts system_prompt and forwards it as camelCase."""
    ax = AsyncExa(API_KEY)
    mock_response = {
        "results": [{"url": "http://example.com", "id": "1", "title": "Async Result"}],
        "costDollars": {"total": 0.001},
    }

    with patch.object(
        ax, "async_request", new=AsyncMock(return_value=mock_response)
    ) as mock_async_request:
        resp = await ax.search(
            "async search query",
            type="auto",
            system_prompt="Prefer official sources and avoid duplicate results",
        )
        assert isinstance(resp, exa_api.SearchResponse)

        call_args = mock_async_request.call_args
        assert call_args[0][0] == "/search"
        options = call_args[0][1]
        assert options["type"] == "auto"
        assert (
            options["systemPrompt"]
            == "Prefer official sources and avoid duplicate results"
        )


@pytest.mark.asyncio
async def test_async_search_accepts_deep_lite_additional_queries_offline():
    """Test async deep-lite search accepts additional_queries."""
    ax = AsyncExa(API_KEY)
    mock_response = {
        "results": [{"url": "http://example.com", "id": "1", "title": "Async Result"}],
        "costDollars": {"total": 0.001},
    }

    with patch.object(
        ax, "async_request", new=AsyncMock(return_value=mock_response)
    ) as mock_async_request:
        resp = await ax.search(
            "async deep query",
            type="deep-lite",
            additional_queries=["ML algorithms", "neural networks", "AI models"],
        )
        assert isinstance(resp, exa_api.SearchResponse)

        call_args = mock_async_request.call_args
        assert call_args[0][0] == "/search"
        options = call_args[0][1]
        assert options["type"] == "deep-lite"
        assert options["additionalQueries"] == [
            "ML algorithms",
            "neural networks",
            "AI models",
        ]


@pytest.mark.asyncio
async def test_async_search_rejects_stream_flag_offline():
    """Test async search(stream=True) points callers to stream_search."""
    ax = AsyncExa(API_KEY)

    with pytest.raises(ValueError, match="Please use `stream_search"):
        await ax.search("streaming query", stream=True)


@pytest.mark.asyncio
async def test_async_stream_search_streams_openai_style_chunks_offline():
    """Test async stream_search forwards stream=true and yields parsed chunks."""
    ax = AsyncExa(API_KEY)
    mock_stream_response = _FakeAsyncStreamResponse(
        [
            'data: {"choices":[{"delta":{"content":"Hello"}}]}',
            'data: {"citations":[{"id":"1","url":"http://example.com","title":"Example"}]}',
        ]
    )

    with patch.object(
        ax, "async_request", new=AsyncMock(return_value=mock_stream_response)
    ) as mock_async_request:
        stream = await ax.stream_search(
            "streaming query",
            type="auto",
            system_prompt="Be concise",
            output_schema={"type": "text", "description": "Short answer"},
        )
        chunks = [chunk async for chunk in stream]

        assert len(chunks) == 2
        assert chunks[0].content == "Hello"
        assert chunks[1].citations is not None
        assert chunks[1].citations[0].url == "http://example.com"

        call_args = mock_async_request.call_args
        assert call_args[0][0] == "/search"
        options = call_args[0][1]
        assert options["stream"] is True
        assert options["type"] == "auto"
        assert options["systemPrompt"] == "Be concise"
        assert options["outputSchema"]["type"] == "text"


@pytest.mark.asyncio
async def test_async_request_accepts_201():
    ax = AsyncExa(API_KEY)

    async def _fake_post(url, json, headers):
        return httpx.Response(201, json={"ok": True})

    with patch.object(ax.client, "post", new=AsyncMock(side_effect=_fake_post)):
        data = await ax.async_request("/dummy", {})
    assert data == {"ok": True}


@pytest.mark.asyncio
async def test_async_request_supports_patch():
    ax = AsyncExa(API_KEY)

    async def _fake_patch(url, json, headers):
        return httpx.Response(200, json={"updated": True})

    with patch.object(ax.client, "patch", new=AsyncMock(side_effect=_fake_patch)):
        data = await ax.async_request("/dummy", {"name": "updated"}, method="PATCH")
    assert data == {"updated": True}


@pytest.mark.asyncio
async def test_async_request_supports_delete():
    ax = AsyncExa(API_KEY)

    async def _fake_delete(url, headers):
        return httpx.Response(200, json={"deleted": True})

    with patch.object(ax.client, "delete", new=AsyncMock(side_effect=_fake_delete)):
        data = await ax.async_request("/dummy", method="DELETE")
    assert data == {"deleted": True}


@pytest.mark.asyncio
async def test_async_request_rejects_unsupported_method():
    ax = AsyncExa(API_KEY)

    with pytest.raises(ValueError, match="Unsupported HTTP method: PUT"):
        await ax.async_request("/dummy", method="PUT")


def test_result_with_highlights_parsing_offline():
    """Test that Result properly parses highlights and highlight_scores."""
    result = exa_api.Result(
        url="http://example.com",
        id="test-id",
        title="Test Title",
        highlights=["highlight 1", "highlight 2"],
        highlight_scores=[0.9, 0.8],
    )
    assert result.highlights == ["highlight 1", "highlight 2"]
    assert result.highlight_scores == [0.9, 0.8]


def test_result_with_highlights_optional_scores_offline():
    """Test that Result works with highlights but without highlight_scores."""
    result = exa_api.Result(
        url="http://example.com",
        id="test-id",
        title="Test Title",
        highlights=["highlight 1"],
        highlight_scores=None,
    )
    assert result.highlights == ["highlight 1"]
    assert result.highlight_scores is None


def test_result_with_full_text_parsing_offline():
    """Test that Result properly parses full_text."""
    result = exa_api.Result(
        url="http://example.com",
        id="test-id",
        title="Test Title",
        full_text="Full page text",
    )
    assert result.full_text == "Full page text"


def test_search_accepts_highlights_option_offline():
    """Test that search method accepts highlights in contents option."""
    exa = Exa(API_KEY)
    mock_response = {
        "results": [
            {
                "url": "http://example.com",
                "id": "1",
                "title": "Test",
                "highlights": ["key point 1", "key point 2"],
                "highlightScores": [0.95, 0.85],
            }
        ],
        "costDollars": {"total": 0.001},
    }

    with patch.object(exa, "request", return_value=mock_response) as mock_request:
        resp = exa.search(
            "test query",
            contents={"highlights": True},
            num_results=1,
        )
        assert isinstance(resp, exa_api.SearchResponse)
        assert resp.results[0].highlights == ["key point 1", "key point 2"]
        assert resp.results[0].highlight_scores == [0.95, 0.85]

        # Verify the request was called with correct parameters
        call_args = mock_request.call_args
        options = call_args[0][1]
        assert "contents" in options
        assert options["contents"]["highlights"] is True


def test_search_accepts_highlights_with_options_offline():
    """Test that search method accepts detailed highlights options."""
    exa = Exa(API_KEY)
    mock_response = {
        "results": [
            {
                "url": "http://example.com",
                "id": "1",
                "title": "Test",
                "highlights": ["highlight 1"],
                "highlightScores": [0.9],
            }
        ],
        "costDollars": {"total": 0.001},
    }

    with patch.object(exa, "request", return_value=mock_response) as mock_request:
        resp = exa.search(
            "test query",
            contents={
                "highlights": {
                    "query": "key points",
                    "num_sentences": 2,
                    "highlights_per_url": 3,
                }
            },
            num_results=1,
        )
        assert isinstance(resp, exa_api.SearchResponse)
        assert resp.results[0].highlights == ["highlight 1"]

        # Verify the request was called with correct camelCase parameters
        call_args = mock_request.call_args
        options = call_args[0][1]
        highlights_opts = options["contents"]["highlights"]
        assert highlights_opts["query"] == "key points"
        assert highlights_opts["numSentences"] == 2
        assert highlights_opts["highlightsPerUrl"] == 3


def test_search_accepts_highlights_with_max_characters_offline():
    """Test that search method accepts max_characters in highlights options."""
    exa = Exa(API_KEY)
    mock_response = {
        "results": [
            {
                "url": "http://example.com",
                "id": "1",
                "title": "Test",
                "highlights": ["highlight 1"],
                "highlightScores": [0.9],
            }
        ],
        "costDollars": {"total": 0.001},
    }

    with patch.object(exa, "request", return_value=mock_response) as mock_request:
        resp = exa.search(
            "test query",
            contents={
                "highlights": {
                    "query": "key points",
                    "max_characters": 500,
                }
            },
            num_results=1,
        )
        assert isinstance(resp, exa_api.SearchResponse)
        assert resp.results[0].highlights == ["highlight 1"]

        # Verify the request was called with correct camelCase parameters
        call_args = mock_request.call_args
        options = call_args[0][1]
        highlights_opts = options["contents"]["highlights"]
        assert highlights_opts["query"] == "key points"
        assert highlights_opts["maxCharacters"] == 500


def test_search_accepts_full_text_option_offline():
    """Test that search accepts full_text and sends fullText."""
    exa = Exa(API_KEY)
    mock_response = {
        "results": [
            {
                "url": "http://example.com",
                "id": "1",
                "title": "Test",
                "fullText": "Full page text",
            }
        ],
        "costDollars": {"total": 0.001},
    }

    with patch.object(exa, "request", return_value=mock_response) as mock_request:
        resp = exa.search(
            "test query",
            contents={"full_text": {"max_characters": 1000}},
            num_results=1,
        )
        assert isinstance(resp, exa_api.SearchResponse)
        assert resp.results[0].full_text == "Full page text"

        call_args = mock_request.call_args
        options = call_args[0][1]
        assert options["contents"]["fullText"]["maxCharacters"] == 1000
        assert "text" not in options["contents"]


def test_crawl_date_parsing_offline():
    """Test that Result properly parses crawl_date from API response."""
    exa = Exa(API_KEY)
    mock_response = {
        "results": [
            {
                "url": "http://example.com",
                "id": "1",
                "title": "Test",
                "text": "Sample text",
                "crawlDate": "2026-04-14T12:31:28.000Z",
            }
        ],
        "costDollars": {"total": 0.001},
    }

    with patch.object(exa, "request", return_value=mock_response):
        resp = exa.search("test query", contents={"text": True}, num_results=1)
        assert isinstance(resp, exa_api.SearchResponse)
        assert resp.results[0].crawl_date == "2026-04-14T12:31:28.000Z"


def test_crawl_date_defaults_to_none_offline():
    """Test that crawl_date is None when not present in API response."""
    exa = Exa(API_KEY)
    mock_response = {
        "results": [
            {
                "url": "http://example.com",
                "id": "1",
                "title": "Test",
            }
        ],
        "costDollars": {"total": 0.001},
    }

    with patch.object(exa, "request", return_value=mock_response):
        resp = exa.search("test query", num_results=1)
        assert isinstance(resp, exa_api.SearchResponse)
        assert resp.results[0].crawl_date is None


def test_crawl_date_on_result_dataclass_offline():
    """Test that crawl_date can be set directly on Result objects."""
    result = exa_api.Result(
        url="http://example.com",
        id="test-id",
        title="Test Title",
        crawl_date="2026-04-14T12:31:28.000Z",
    )
    assert result.crawl_date == "2026-04-14T12:31:28.000Z"

    result_no_crawl = exa_api.Result(
        url="http://example.com",
        id="test-id",
        title="Test Title",
    )
    assert result_no_crawl.crawl_date is None


@pytest.mark.asyncio
async def test_async_crawl_date_parsing_offline():
    """Test that AsyncExa properly parses crawl_date from API response."""
    ax = AsyncExa(API_KEY)
    mock_response = {
        "results": [
            {
                "url": "http://example.com",
                "id": "1",
                "title": "Test",
                "crawlDate": "2026-04-14T12:31:28.000Z",
            }
        ],
        "costDollars": {"total": 0.001},
    }

    with patch.object(
        ax, "async_request", new=AsyncMock(return_value=mock_response)
    ):
        resp = await ax.search("test query", num_results=1)
        assert isinstance(resp, exa_api.SearchResponse)
        assert resp.results[0].crawl_date == "2026-04-14T12:31:28.000Z"


def test_search_and_contents_with_highlights_offline():
    """Test deprecated search_and_contents method with highlights."""
    exa = Exa(API_KEY)
    mock_response = {
        "results": [
            {
                "url": "http://example.com",
                "id": "1",
                "title": "Test",
                "text": "Sample text",
                "highlights": ["key point"],
                "highlightScores": [0.9],
            }
        ],
        "costDollars": {"total": 0.001},
    }

    with patch.object(exa, "request", return_value=mock_response) as mock_request:
        resp = exa.search_and_contents(
            "test query",
            text=True,
            highlights=True,
            num_results=1,
        )
        assert isinstance(resp, exa_api.SearchResponse)
        assert resp.results[0].text == "Sample text"
        assert resp.results[0].highlights == ["key point"]

        # Verify highlights is nested under contents
        call_args = mock_request.call_args
        options = call_args[0][1]
        assert options["contents"]["highlights"] is True
        assert options["contents"]["text"] is True


def test_search_and_contents_with_full_text_offline():
    """Test deprecated search_and_contents method with full_text."""
    exa = Exa(API_KEY)
    mock_response = {
        "results": [
            {
                "url": "http://example.com",
                "id": "1",
                "title": "Test",
                "fullText": "Full page text",
            }
        ],
        "costDollars": {"total": 0.001},
    }

    with patch.object(exa, "request", return_value=mock_response) as mock_request:
        resp = exa.search_and_contents(
            "test query",
            full_text={"max_characters": 1000},
            num_results=1,
        )
        assert isinstance(resp, exa_api.SearchResponse)
        assert resp.results[0].full_text == "Full page text"

        call_args = mock_request.call_args
        options = call_args[0][1]
        assert options["contents"]["fullText"]["maxCharacters"] == 1000
        assert "text" not in options["contents"]


def test_get_contents_with_full_text_offline():
    """Test get_contents with full_text."""
    exa = Exa(API_KEY)
    mock_response = {
        "results": [
            {
                "url": "http://example.com",
                "id": "1",
                "title": "Test",
                "fullText": "Full page text",
            }
        ],
        "costDollars": {"total": 0.001},
    }

    with patch.object(exa, "request", return_value=mock_response) as mock_request:
        resp = exa.get_contents(
            ["http://example.com"],
            full_text={"max_characters": 1000},
        )
        assert isinstance(resp, exa_api.SearchResponse)
        assert resp.results[0].full_text == "Full page text"

        call_args = mock_request.call_args
        options = call_args[0][1]
        assert options["fullText"]["maxCharacters"] == 1000
        assert "text" not in options


def test_get_contents_with_query_guided_text_offline():
    """Test get_contents passes query-guided text options."""
    exa = Exa(API_KEY)
    mock_response = {
        "results": [
            {
                "url": "http://example.com",
                "id": "1",
                "title": "Test",
                "text": "Focused text excerpt",
            }
        ],
        "costDollars": {"total": 0.001},
    }

    with patch.object(exa, "request", return_value=mock_response) as mock_request:
        resp = exa.get_contents(
            ["http://example.com"],
            text={"query": "when did they graduate", "max_characters": 1000},
        )
        assert isinstance(resp, exa_api.SearchResponse)
        assert resp.results[0].text == "Focused text excerpt"

        call_args = mock_request.call_args
        options = call_args[0][1]
        assert options["text"]["query"] == "when did they graduate"
        assert options["text"]["maxCharacters"] == 1000
        assert "fullText" not in options


@pytest.mark.asyncio
async def test_async_get_contents_with_full_text_offline():
    """Test async get_contents with full_text."""
    ax = AsyncExa(API_KEY)
    mock_response = {
        "results": [
            {
                "url": "http://example.com",
                "id": "1",
                "title": "Test",
                "fullText": "Full page text",
            }
        ],
        "costDollars": {"total": 0.001},
    }

    with patch.object(
        ax, "async_request", new=AsyncMock(return_value=mock_response)
    ) as mock_request:
        resp = await ax.get_contents(
            ["http://example.com"],
            full_text={"max_characters": 1000},
        )
        assert isinstance(resp, exa_api.SearchResponse)
        assert resp.results[0].full_text == "Full page text"

        call_args = mock_request.call_args
        options = call_args[0][1]
        assert options["fullText"]["maxCharacters"] == 1000
        assert "text" not in options


@pytest.mark.asyncio
async def test_async_get_contents_with_query_guided_text_offline():
    """Test async get_contents passes query-guided text options."""
    ax = AsyncExa(API_KEY)
    mock_response = {
        "results": [
            {
                "url": "http://example.com",
                "id": "1",
                "title": "Test",
                "text": "Focused text excerpt",
            }
        ],
        "costDollars": {"total": 0.001},
    }

    with patch.object(
        ax, "async_request", new=AsyncMock(return_value=mock_response)
    ) as mock_request:
        resp = await ax.get_contents(
            ["http://example.com"],
            text={"query": "when did they graduate", "max_characters": 1000},
        )
        assert isinstance(resp, exa_api.SearchResponse)
        assert resp.results[0].text == "Focused text excerpt"

        call_args = mock_request.call_args
        options = call_args[0][1]
        assert options["text"]["query"] == "when did they graduate"
        assert options["text"]["maxCharacters"] == 1000
        assert "fullText" not in options


########################################
# Live integration tests (skipped without key)
########################################


@pytest.mark.skipif(not _have_real_key(), reason="EXA_API_KEY not provided")
def test_user_agent_header():
    exa = Exa(API_KEY)
    # Get the expected version dynamically
    expected_version = exa_api._get_package_version()
    expected_user_agent = f"exa-py/{expected_version}"
    assert exa.headers["User-Agent"] == expected_user_agent


@pytest.mark.skipif(not _have_real_key(), reason="EXA_API_KEY not provided")
def test_research_client_attrs():
    exa = Exa(API_KEY)
    aexa = AsyncExa(API_KEY)
    assert hasattr(exa, "research") and hasattr(aexa, "research")


# ---- Core live endpoint smoke checks ----


@pytest.mark.skipif(not _have_real_key(), reason="EXA_API_KEY not provided")
def test_get_contents_live_preferred():
    exa = Exa(API_KEY)
    resp = exa.get_contents(
        urls=["https://techcrunch.com"], text=True, livecrawl="preferred"
    )
    assert isinstance(resp, exa_api.SearchResponse)
    # statuses may be empty when cached – still fine
    assert len(resp.results) >= 1


@pytest.mark.skipif(not _have_real_key(), reason="EXA_API_KEY not provided")
def test_search_and_contents_live():
    exa = Exa(API_KEY)
    resp = exa.search_and_contents("openai", num_results=1, text=True)
    assert resp.results and resp.results[0].text


@pytest.mark.skipif(not _have_real_key(), reason="EXA_API_KEY not provided")
def test_search_with_user_location_live():
    exa = Exa(API_KEY)
    resp = exa.search("news", num_results=1, user_location="US")
    assert resp.results


@pytest.mark.skipif(not _have_real_key(), reason="EXA_API_KEY not provided")
def test_find_similar_live():
    exa = Exa(API_KEY)
    resp = exa.find_similar("https://example.com", num_results=1)
    assert resp.results


@pytest.mark.skipif(not _have_real_key(), reason="EXA_API_KEY not provided")
def test_get_contents_sync_live():
    exa = Exa(API_KEY)
    resp = exa.get_contents(urls=["https://example.com"], text=True, livecrawl="never")
    assert resp.results


@pytest.mark.asyncio
@pytest.mark.skipif(not _have_real_key(), reason="EXA_API_KEY not provided")
async def test_get_contents_async_live():
    ax = AsyncExa(API_KEY)
    resp = await ax.get_contents(
        urls=["https://example.com"], text=True, livecrawl="never"
    )
    assert resp.results


########################################
# Live tests for new context / statuses features
########################################


@pytest.mark.skipif(not _have_real_key(), reason="EXA_API_KEY not provided")
def test_search_and_contents_context_live():
    """search_and_contents with context=True should return non-empty context string."""
    exa = Exa(API_KEY)
    resp = exa.search_and_contents(
        "openai research", num_results=3, context=True, text=False
    )
    assert (
        resp.context is not None
        and isinstance(resp.context, str)
        and len(resp.context) > 0
    )


@pytest.mark.skipif(not _have_real_key(), reason="EXA_API_KEY not provided")
def test_find_similar_and_contents_context_live():
    """find_similar_and_contents with context flag should include context string."""
    exa = Exa(API_KEY)
    resp = exa.find_similar_and_contents(
        "https://example.com", num_results=3, context=True, text=False
    )
    # context may be empty depending on backend, but attribute should exist (None or str)
    assert hasattr(resp, "context")


@pytest.mark.skipif(not _have_real_key(), reason="EXA_API_KEY not provided")
def test_get_contents_statuses_live():
    """get_contents should expose statuses list (possibly empty)."""
    exa = Exa(API_KEY)
    resp = exa.get_contents(
        urls=["https://techcrunch.com"], text=True, livecrawl="never"
    )
    # statuses attribute exists; ensure it's a list
    assert isinstance(resp.statuses, list)


########################################
# Live tests for highlights feature
########################################


@pytest.mark.skipif(not _have_real_key(), reason="EXA_API_KEY not provided")
def test_search_with_highlights_live():
    """search with highlights option should return highlights in results."""
    exa = Exa(API_KEY)
    resp = exa.search(
        "openai research",
        contents={"highlights": True},
        num_results=2,
    )
    assert isinstance(resp, exa_api.SearchResponse)
    assert len(resp.results) > 0
    # At least one result should have highlights
    has_highlights = any(r.highlights is not None for r in resp.results)
    assert has_highlights, "Expected at least one result with highlights"


@pytest.mark.skipif(not _have_real_key(), reason="EXA_API_KEY not provided")
def test_search_with_highlights_options_live():
    """search with detailed highlights options should work."""
    exa = Exa(API_KEY)
    resp = exa.search(
        "machine learning",
        contents={
            "highlights": {
                "num_sentences": 2,
                "highlights_per_url": 3,
            }
        },
        num_results=2,
    )
    assert isinstance(resp, exa_api.SearchResponse)
    assert len(resp.results) > 0


@pytest.mark.skipif(not _have_real_key(), reason="EXA_API_KEY not provided")
def test_search_and_contents_with_highlights_live():
    """search_and_contents with highlights option should return highlights."""
    exa = Exa(API_KEY)
    resp = exa.search_and_contents(
        "artificial intelligence",
        highlights=True,
        num_results=2,
    )
    assert isinstance(resp, exa_api.SearchResponse)
    assert len(resp.results) > 0
    # At least one result should have highlights
    has_highlights = any(r.highlights is not None for r in resp.results)
    assert has_highlights, "Expected at least one result with highlights"
