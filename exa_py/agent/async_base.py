"""Async base client classes for the Exa Agent API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional, Sequence, Union

import httpx

if TYPE_CHECKING:
    from exa_py.api import AsyncExa


class AsyncAgentBaseClient:
    """Base client for asynchronous Agent API operations."""

    def __init__(self, client: "AsyncExa"):
        self._client = client
        self.base_path = "/agent/runs"

    async def request(
        self,
        endpoint: str,
        *,
        betas: Sequence[str],
        method: str = "POST",
        data: Optional[Union[Dict[str, Any], str]] = None,
        params: Optional[Dict[str, str]] = None,
        stream: bool = False,
        headers: Optional[Dict[str, str]] = None,
    ) -> Union[Dict[str, Any], httpx.Response]:
        if not betas:
            raise ValueError("betas must include the Agent API beta identifier")
        full_endpoint = f"{self.base_path}{endpoint}"
        request_headers = {"Exa-Beta": ",".join(betas)}
        if stream:
            request_headers["Accept"] = "text/event-stream"
        if headers:
            request_headers.update(headers)
        return await self._client.async_request(
            full_endpoint,
            data=data,
            method=method,
            params=params,
            headers=request_headers,
        )

    def build_pagination_params(
        self,
        cursor: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, str]:
        params: Dict[str, str] = {}
        if cursor is not None:
            params["cursor"] = cursor
        if limit is not None:
            params["limit"] = str(limit)
        return params
