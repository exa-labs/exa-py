"""Base client classes for the Research API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional, Union

import httpx
import requests

if TYPE_CHECKING:
    from exa_py.api import Exa, AsyncExa


class ResearchBaseClient:
    """Base client for synchronous Research API operations."""

    def __init__(self, client: "Exa"):
        """Initialize the base client.

        Args:
            client: The parent Exa client instance.
        """
        self._client = client
        self.base_path = "/research/v1"

    def request(
        self,
        endpoint: str,
        method: str = "POST",
        data: Optional[Union[Dict[str, Any], str]] = None,
        params: Optional[Dict[str, str]] = None,
        stream: bool = False,
    ) -> Union[Dict[str, Any], requests.Response]:
        """Make a request to the Research API.

        Args:
            endpoint: The API endpoint (relative to base_path).
            method: HTTP method to use.
            data: Request body data.
            params: Query parameters.
            stream: Whether to stream the response.

        Returns:
            The API response as a dict or raw Response for streaming.
        """
        full_endpoint = f"{self.base_path}{endpoint}"

        if stream:
            # For streaming, handle differently based on method
            if method == "GET":
                # For GET requests, streaming is controlled by params
                # The params should already have stream=true set by the caller
                return self._client.request(
                    full_endpoint, data=None, method=method, params=params
                )
            else:
                # For POST requests, add stream flag to data
                if data is None:
                    data = {}
                if isinstance(data, dict):
                    data["stream"] = True
                # The client's request method returns raw Response when streaming
                return self._client.request(
                    full_endpoint, data=data, method=method, params=params
                )
        else:
            return self._client.request(
                full_endpoint, data=data, method=method, params=params
            )

    def build_pagination_params(
        self, cursor: Optional[str] = None, limit: Optional[int] = None
    ) -> Dict[str, str]:
        """Build pagination parameters for list requests.

        Args:
            cursor: Pagination cursor.
            limit: Maximum number of results.

        Returns:
            Dictionary of query parameters.
        """
        params = {}
        if cursor is not None:
            params["cursor"] = cursor
        if limit is not None:
            params["limit"] = str(limit)
        return params


class AsyncResearchBaseClient:
    """Base client for asynchronous Research API operations."""

    def __init__(self, client: "AsyncExa"):
        """Initialize the async base client.

        Args:
            client: The parent AsyncExa client instance.
        """
        self._client = client
        self.base_path = "/research/v1"

    async def request(
        self,
        endpoint: str,
        method: str = "POST",
        data: Optional[Union[Dict[str, Any], str]] = None,
        params: Optional[Dict[str, str]] = None,
        stream: bool = False,
    ) -> Union[Dict[str, Any], httpx.Response]:
        """Make an async request to the Research API.

        Args:
            endpoint: The API endpoint (relative to base_path).
            method: HTTP method to use.
            data: Request body data.
            params: Query parameters.
            stream: Whether to stream the response.

        Returns:
            The API response as a dict or raw Response for streaming.
        """
        full_endpoint = f"{self.base_path}{endpoint}"

        if stream:
            # For streaming, handle differently based on method
            if method == "GET":
                # For GET requests, streaming is controlled by params
                # The params should already have stream=true set by the caller
                return await self._client.async_request(
                    full_endpoint, data=None, method=method, params=params
                )
            else:
                # For POST requests, add stream flag to data
                if data is None:
                    data = {}
                if isinstance(data, dict):
                    data["stream"] = True
                # The async_request method returns raw Response when streaming
                return await self._client.async_request(
                    full_endpoint, data=data, method=method, params=params
                )
        else:
            return await self._client.async_request(
                full_endpoint, data=data, method=method, params=params
            )

    def build_pagination_params(
        self, cursor: Optional[str] = None, limit: Optional[int] = None
    ) -> Dict[str, str]:
        """Build pagination parameters for list requests.

        Args:
            cursor: Pagination cursor.
            limit: Maximum number of results.

        Returns:
            Dictionary of query parameters.
        """
        params = {}
        if cursor is not None:
            params["cursor"] = cursor
        if limit is not None:
            params["limit"] = str(limit)
        return params
