"""Base client classes for the Research API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, NoReturn, Optional, Union
from typing_extensions import Unpack

import httpx
import requests
from ..request_options import ExtraRequestOptions

if TYPE_CHECKING:
    from exa_py.api import Exa, AsyncExa


RESEARCH_RETIRED_MESSAGE = (
    "The Exa Research API has been retired and no longer accepts requests. "
    "Use the Agent API (exa.agent.runs.create) for asynchronous, multi-step research."
)


def raise_research_retired() -> NoReturn:
    """Raise the error that every Research API method raises.

    Raises:
        ValueError: Always, with a message that names the Agent API as the replacement.
    """
    raise ValueError(RESEARCH_RETIRED_MESSAGE)


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
        **extra: Unpack[ExtraRequestOptions],
    ) -> Union[Dict[str, Any], requests.Response]:
        """Make a request to the Research API.

        Args:
            endpoint: The API endpoint (relative to base_path).
            method: HTTP method to use.
            data: Request body data.
            params: Query parameters.
            stream: Whether to stream the response.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).

        Returns:
            The API response as a dict or raw Response for streaming.

        Raises:
            ValueError: Always. The Research API has been retired.
        """
        raise_research_retired()

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
        **extra: Unpack[ExtraRequestOptions],
    ) -> Union[Dict[str, Any], httpx.Response]:
        """Make an async request to the Research API.

        Args:
            endpoint: The API endpoint (relative to base_path).
            method: HTTP method to use.
            data: Request body data.
            params: Query parameters.
            stream: Whether to stream the response.
            **extra: Per-call request options (``extra_headers``, ``extra_query``, ``extra_body``).

        Returns:
            The API response as a dict or raw Response for streaming.

        Raises:
            ValueError: Always. The Research API has been retired.
        """
        raise_research_retired()

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
