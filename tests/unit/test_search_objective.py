import json
from unittest.mock import Mock, patch

import httpx
import pytest

from exa_py import AsyncExa, Exa


@pytest.mark.parametrize("method", ["search", "search_and_contents", "stream_search"])
@pytest.mark.parametrize("objective", [None, "Compare GPU providers", ""])
@pytest.mark.parametrize("beta_header", [None, "another-token"])
def test_search_objective_wire_payload(method, objective, beta_header):
    client = Exa("test-key")
    if beta_header is not None:
        client.headers["exa-beta"] = beta_header
    response = Mock(status_code=200)
    response.json.return_value = {"results": []}
    with patch("exa_py.api.requests.post", return_value=response) as post:
        getattr(client, method)("H100 pricing", objective=objective)
    body = json.loads(post.call_args.kwargs["data"])
    assert body.get("objective") == objective
    headers = {
        key.lower(): value for key, value in post.call_args.kwargs["headers"].items()
    }
    assert headers.get("exa-beta") == beta_header


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["search", "search_and_contents", "stream_search"])
@pytest.mark.parametrize("objective", [None, "Compare GPU providers", ""])
@pytest.mark.parametrize("beta_header", [None, "another-token"])
async def test_async_search_objective_wire_payload(method, objective, beta_header):
    received = []

    def respond(request):
        received.append(request)
        return httpx.Response(200, json={"results": []})

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as transport:
        client = AsyncExa("test-key")
        client._client = transport
        if beta_header is not None:
            client.headers["exa-beta"] = beta_header
        await getattr(client, method)("H100 pricing", objective=objective)
    assert json.loads(received[0].content).get("objective") == objective
    assert received[0].headers.get("exa-beta") == beta_header
