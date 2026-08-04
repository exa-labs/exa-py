"""Async base client classes for the Exa Agent Monitors API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional, Union

if TYPE_CHECKING:
    from exa_py.api import AsyncExa


class AsyncAgentMonitorsBaseClient:
    """Base client for asynchronous Agent Monitors API operations."""

    def __init__(self, client: "AsyncExa"):
        self._client = client
        self.base_path = "/agent/monitors"

    async def request(
        self,
        endpoint: str,
        *,
        method: str = "POST",
        data: Optional[Union[Dict[str, Any], str]] = None,
        params: Optional[Dict[str, str]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        full_endpoint = f"{self.base_path}{endpoint}"
        return await self._client.async_request(
            full_endpoint,
            data=data,
            method=method,
            params=params,
            headers=headers or {},
        )

    def build_pagination_params(
        self,
        cursor: Optional[str] = None,
        limit: Optional[int] = None,
        since: Optional[str] = None,
    ) -> Dict[str, str]:
        params: Dict[str, str] = {}
        if cursor is not None:
            params["cursor"] = cursor
        if limit is not None:
            params["limit"] = str(limit)
        if since is not None:
            params["since"] = since
        return params
