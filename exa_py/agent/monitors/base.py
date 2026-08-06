"""Base client classes for the Exa Agent Monitors API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional, Sequence, Union

from ..betas import headers_for_betas
from .types import AGENT_MONITORS_BETA_HEADER

if TYPE_CHECKING:
    from exa_py.api import Exa


class AgentMonitorsBaseClient:
    """Base client for synchronous Agent Monitors API operations."""

    def __init__(self, client: "Exa"):
        self._client = client
        self.base_path = "/agent/monitors"

    def request(
        self,
        endpoint: str,
        *,
        betas: Sequence[str],
        method: str = "POST",
        data: Optional[Union[Dict[str, Any], str]] = None,
        params: Optional[Dict[str, str]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        if not betas or AGENT_MONITORS_BETA_HEADER not in betas:
            raise ValueError(
                "betas must include the Agent Monitors beta identifier "
                f'("{AGENT_MONITORS_BETA_HEADER}")'
            )
        full_endpoint = f"{self.base_path}{endpoint}"
        request_headers = dict(headers_for_betas(betas) or {})
        if headers:
            request_headers.update(headers)
        return self._client.request(
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
