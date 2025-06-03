"""Lightweight research client wrappers for the Exa REST API.

This module purposefully keeps its import surface minimal to avoid circular
import problems with :pymod:`exa_py.api`.  Any heavy dependencies (including
`exa_py.api` itself) are imported lazily **inside** functions.  This means
that type-checkers still see the full, precise types via the ``TYPE_CHECKING``
block, but at runtime we only pay the cost if/when a helper is actually used.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional, Literal

if TYPE_CHECKING:  # pragma: no cover – only for static analysers
    # Import with full type info when static type-checking.  `_Result` still
    # lives in ``exa_py.api`` but the response model moved to
    # ``exa_py.research.models``.
    from ..api import _Result  # noqa: F401
    from .models import (
        ResearchTask,
        ResearchTaskId,
        ListResearchTasksResponse,
    )  # noqa: F401

# ---------------------------------------------------------------------------
# Public, user-facing clients
# ---------------------------------------------------------------------------


class ResearchClient:
    """Synchronous helper namespace accessed via :pyattr:`Exa.research`."""

    def __init__(self, parent_client):
        # A reference to the *already-constructed* ``Exa`` instance so that we
        # can piggy-back on its HTTP plumbing (headers, base URL, retries, …).
        self._client = parent_client

    def create_task(
        self,
        *,
        instructions: str,
        model: Literal["exa-research", "exa-research-pro"] = "exa-research",
        output_infer_schema: bool = None,
        output_schema: Dict[str, Any] = None,
    ) -> "ResearchTaskId":
        """Submit a research request and return the *task identifier*."""
        payload = {"instructions": instructions}
        if model is not None:
            payload["model"] = model
        if output_schema is not None or output_infer_schema is not None:
            payload["output"] = {}
            if output_schema is not None:
                payload["output"]["schema"] = output_schema
            if output_infer_schema is not None:
                payload["output"]["inferSchema"] = output_infer_schema

        raw_response: Dict[str, Any] = self._client.request(
            "/research/v0/tasks", payload
        )

        # Defensive checks so that we fail loudly if the contract changes.
        if not isinstance(raw_response, dict) or "id" not in raw_response:
            raise RuntimeError(
                f"Unexpected response while creating research task: {raw_response}"
            )

        # Lazily import to avoid circular deps at runtime.
        from .models import ResearchTaskId  # noqa: WPS433 – runtime import

        return ResearchTaskId(id=raw_response["id"])

    def get_task(self, id: str) -> "ResearchTask":  # noqa: D401 – imperative mood is fine
        """Fetch the current status / result for a research task."""
        endpoint = f"/research/v0/tasks/{id}"

        # The new endpoint is a simple GET.
        raw_response: Dict[str, Any] = self._client.request(endpoint, method="GET")

        return _build_research_task(raw_response)

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def poll_task(
        self,
        id: str,
        *,
        poll_interval: float = 1.0,
        timeout_seconds: int = 15 * 60,
    ) -> "ResearchTask":
        """Blocking helper that polls until task completes or fails.

        Parameters
        ----------
        id:
            The ID of the research task to poll.
        poll_interval:
            Seconds to wait between successive polls (default 1s).
        timeout_seconds:
            Maximum time to wait before raising :class:`TimeoutError` (default 15 min).
        """

        import time

        deadline = time.monotonic() + timeout_seconds

        while True:
            task = self.get_task(id)
            status = task.status.lower() if isinstance(task.status, str) else ""

            if status in {"completed", "failed", "complete", "finished", "done"}:
                return task

            if time.monotonic() > deadline:
                raise TimeoutError(
                    f"Research task {id} did not finish within {timeout_seconds} seconds"
                )

            time.sleep(poll_interval)

    # ------------------------------------------------------------------
    # Listing helpers
    # ------------------------------------------------------------------

    def list(
        self,
        *,
        cursor: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> "ListResearchTasksResponse":
        """List research tasks with optional pagination.

        Parameters
        ----------
        cursor:
            Pagination cursor returned by a previous call (optional).
        limit:
            Maximum number of tasks to return (optional).
        """

        params = {
            k: v for k, v in {"cursor": cursor, "limit": limit}.items() if v is not None
        }

        raw_response: Dict[str, Any] = self._client.request(
            "/research/v0/tasks",
            data=None,
            method="GET",
            params=params or None,
        )

        # Defensive checks so that we fail loudly if the contract changes.
        if not isinstance(raw_response, dict) or "data" not in raw_response:
            raise RuntimeError(
                f"Unexpected response while listing research tasks: {raw_response}"
            )

        tasks = [_build_research_task(t) for t in raw_response.get("data", [])]

        # Lazy import to avoid cycles.
        from .models import ListResearchTasksResponse  # noqa: WPS433 – runtime import

        return ListResearchTasksResponse(
            data=tasks,
            has_more=raw_response.get("hasMore", False),
            next_cursor=raw_response.get("nextCursor"),
        )


class AsyncResearchClient:
    """Async counterpart used via :pyattr:`AsyncExa.research`."""

    def __init__(self, parent_client):
        self._client = parent_client

    async def create_task(
        self,
        *,
        instructions: str,
        model: Literal["exa-research", "exa-research-pro"] = "exa-research",
        output_schema: Dict[str, Any],
    ) -> "ResearchTaskId":
        """Submit a research request and return the *task identifier* (async)."""

        payload = {
            "instructions": instructions,
            "model": model,
            "output": {"schema": output_schema},
        }

        raw_response: Dict[str, Any] = await self._client.async_request(
            "/research/v0/tasks", payload
        )

        # Defensive checks so that we fail loudly if the contract changes.
        if not isinstance(raw_response, dict) or "id" not in raw_response:
            raise RuntimeError(
                f"Unexpected response while creating research task: {raw_response}"
            )

        # Lazily import to avoid circular deps at runtime.
        from .models import ResearchTaskId  # noqa: WPS433 – runtime import

        return ResearchTaskId(id=raw_response["id"])

    async def get_task(self, id: str) -> "ResearchTask":  # noqa: D401
        """Fetch the current status / result for a research task (async)."""

        endpoint = f"/research/v0/tasks/{id}"

        # Perform GET using the underlying HTTP client because `async_request`
        # only supports POST semantics.
        resp = await self._client.client.get(
            self._client.base_url + endpoint, headers=self._client.headers
        )

        if resp.status_code >= 400:
            raise RuntimeError(
                f"Request failed with status code {resp.status_code}: {resp.text}"
            )

        raw_response: Dict[str, Any] = resp.json()

        return _build_research_task(raw_response)

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    async def poll_task(
        self,
        id: str,
        *,
        poll_interval: float = 1.0,
        timeout_seconds: int = 15 * 60,
    ) -> "ResearchTask":
        """Async helper that polls until task completes or fails.

        Mirrors :py:meth:`ResearchClient.poll_task` but uses ``await`` and
        :pyfunc:`asyncio.sleep`.  Raises :class:`TimeoutError` on timeout.
        """

        import asyncio
        import time

        deadline = time.monotonic() + timeout_seconds

        while True:
            task = await self.get_task(id)
            status = task.status.lower() if isinstance(task.status, str) else ""

            if status in {"completed", "failed", "complete", "finished", "done"}:
                return task

            if time.monotonic() > deadline:
                raise TimeoutError(
                    f"Research task {id} did not finish within {timeout_seconds} seconds"
                )

            await asyncio.sleep(poll_interval)

    # ------------------------------------------------------------------
    # Listing helpers
    # ------------------------------------------------------------------

    async def list(
        self,
        *,
        cursor: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> "ListResearchTasksResponse":
        """Async list of research tasks with optional pagination."""

        params = {
            k: v for k, v in {"cursor": cursor, "limit": limit}.items() if v is not None
        }

        resp = await self._client.client.get(
            self._client.base_url + "/research/v0/tasks",
            headers=self._client.headers,
            params=params or None,
        )

        if resp.status_code >= 400:
            raise RuntimeError(
                f"Request failed with status code {resp.status_code}: {resp.text}"
            )

        raw_response: Dict[str, Any] = resp.json()

        if not isinstance(raw_response, dict) or "data" not in raw_response:
            raise RuntimeError(
                f"Unexpected response while listing research tasks: {raw_response}"
            )

        tasks = [_build_research_task(t) for t in raw_response.get("data", [])]

        from .models import ListResearchTasksResponse  # noqa: WPS433 – runtime import

        return ListResearchTasksResponse(
            data=tasks,
            has_more=raw_response.get("hasMore", False),
            next_cursor=raw_response.get("nextCursor"),
        )


# ---------------------------------------------------------------------------
# Internal helpers (lazy imports to avoid cycles)
# ---------------------------------------------------------------------------


def _build_research_task(raw: Dict[str, Any]):
    """Convert raw API response into a :class:`ResearchTask` instance."""

    # Defensive check – fail loudly if the API contract changes.
    if not isinstance(raw, dict) or "id" not in raw:
        raise RuntimeError(f"Unexpected response while fetching research task: {raw}")

    # Lazily import heavy deps to avoid cycles and unnecessary startup cost.
    from .models import ResearchTask  # noqa: WPS433 – runtime import
    from ..api import _Result, to_snake_case  # noqa: WPS433 – runtime import

    citations_raw = raw.get("citations", {}) or {}
    citations_parsed = {
        key: [_Result(**to_snake_case(c)) for c in cites]
        for key, cites in citations_raw.items()
    }

    return ResearchTask(
        id=raw["id"],
        status=raw["status"],
        instructions=raw.get("instructions", ""),
        schema=raw.get("schema", {}),
        data=raw.get("data"),
        citations=citations_parsed,
    )
