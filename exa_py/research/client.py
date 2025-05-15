"""Lightweight research client wrappers for the Exa REST API.

This module purposefully keeps its import surface minimal to avoid circular
import problems with :pymod:`exa_py.api`.  Any heavy dependencies (including
`exa_py.api` itself) are imported lazily **inside** functions.  This means
that type-checkers still see the full, precise types via the ``TYPE_CHECKING``
block, but at runtime we only pay the cost if/when a helper is actually used.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:  # pragma: no cover – only for static analysers
    # These imports are safe during type-checking because there is no runtime
    # execution order to worry about.  At runtime we *must* avoid them to
    # prevent a circular import (``exa_py.api`` -> ``ResearchClient`` ->
    # ``exa_py.api``).
    from ..api import ResearchTaskResponse, _Result  # noqa: F401

# ---------------------------------------------------------------------------
# Public, user-facing clients
# ---------------------------------------------------------------------------


class ResearchClient:
    """Synchronous helper namespace accessed via :pyattr:`Exa.research`."""

    def __init__(self, parent_client):
        # A reference to the *already-constructed* ``Exa`` instance so that we
        # can piggy-back on its HTTP plumbing (headers, base URL, retries, …).
        self._client = parent_client

    # ------------------------------------------------------------------
    # API surface
    # ------------------------------------------------------------------
    def create_task(
        self,
        *,
        input_instructions: str,
        output_schema: Dict[str, Any],
    ) -> "ResearchTaskResponse":
        """Submit a research request to the Exa backend.

        Parameters
        ----------
        input_instructions:
            Natural-language instructions that describe *what* should be
            researched or extracted.
        output_schema:
            JSON-schema describing the desired structured output format.
        """
        payload = {
            "input": {"instructions": input_instructions},
            "output": {"schema": output_schema},
        }
        response = self._client.request("/research/tasks", payload)
        return _parse_research_response(response)

    def get_task(self, id: str):  # noqa: D401 – imperative mood is fine
        """Placeholder endpoint – not yet implemented on the server side."""
        raise NotImplementedError(
            "`exa.research.get_task` is not available yet. Please open an "
            "issue if you need this sooner."
        )


class AsyncResearchClient:
    """Async counterpart used via :pyattr:`AsyncExa.research`."""

    def __init__(self, parent_client):
        self._client = parent_client

    async def create_task(
        self,
        *,
        input_instructions: str,
        output_schema: Dict[str, Any],
    ) -> "ResearchTaskResponse":
        payload = {
            "input": {"instructions": input_instructions},
            "output": {"schema": output_schema},
        }
        response = await self._client.async_request("/research/tasks", payload)
        return _parse_research_response(response)

    async def get_task(self, id: str):  # noqa: D401
        raise NotImplementedError(
            "`exa.research.get_task` is not available yet. Please open an "
            "issue if you need this sooner."
        )


# ---------------------------------------------------------------------------
# Internal helpers (lazy imports to avoid cycles)
# ---------------------------------------------------------------------------


def _parse_research_response(raw: Dict[str, Any]):
    """Transform camel-case API payload into rich Python objects."""
    from ..api import ResearchTaskResponse, _Result, to_snake_case

    return ResearchTaskResponse(
        id=raw["id"],
        status=raw["status"],
        output=raw.get("output"),
        citations={
            key: [_Result(**to_snake_case(c)) for c in citations]
            for key, citations in raw.get("citations", {}).items()
        },
    )
