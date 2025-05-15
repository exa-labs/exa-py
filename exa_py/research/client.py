"""Lightweight research client wrappers for the Exa REST API.

This module purposefully keeps its import surface minimal to avoid circular
import problems with :pymod:`exa_py.api`.  Any heavy dependencies (including
`exa_py.api` itself) are imported lazily **inside** functions.  This means
that type-checkers still see the full, precise types via the ``TYPE_CHECKING``
block, but at runtime we only pay the cost if/when a helper is actually used.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

if TYPE_CHECKING:  # pragma: no cover – only for static analysers
    # Import with full type info when static type-checking.  `_Result` still
    # lives in ``exa_py.api`` but the response model moved to
    # ``exa_py.research.models``.
    from ..api import _Result  # noqa: F401
    from .models import ResearchTaskResponse  # noqa: F401

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

        The public API remains synchronous – the function only returns once
        the task has finished and the final structured answer is available.
        Internally, however, the endpoint now streams *progress* updates via
        Server-Sent Events (SSE). We therefore initiate a streaming request
        and keep reading until we receive the terminal ``{"tag": "complete"}``
        chunk, which carries the exact same payload shape that the blocking
        variant returned previously.  Any ``{"tag": "progress"}`` chunks are
        ignored, while ``{"tag": "error"}`` chunks result in an exception.

        Parameters
        ----------
        input_instructions:
            Natural-language instructions that describe *what* should be
            researched or extracted.
        output_schema:
            JSON-schema describing the desired structured output format.
        """

        import json

        payload = {
            "input": {"instructions": input_instructions},
            "output": {"schema": output_schema},
        }

        raw_response = self._client.request(
            "/research/tasks", payload, force_stream=True
        )

        def _handle_payload(tag: Optional[str], payload_dict: Dict[str, Any]):
            """Inner helper handling decoded JSON chunks."""
            if tag is None:
                tag_local = payload_dict.get("tag")
            else:
                tag_local = tag

            if tag_local == "progress":
                return None  # ignore
            if tag_local == "error":
                msg = payload_dict.get("error", {}).get("message", "Unknown error")
                raise RuntimeError(f"Research task failed: {msg}")
            if tag_local == "complete":
                data_obj = payload_dict.get("data")
                if data_obj is None:
                    raise RuntimeError("Malformed 'complete' chunk with no data")
                return _parse_research_response(data_obj)

            # Fallback: if looks like final object
            if {"id", "status"}.issubset(payload_dict.keys()):
                return _parse_research_response(payload_dict)
            return None

        # ------------------------------------------------------------------
        # Minimal SSE parser (sync)
        # ------------------------------------------------------------------
        event_name: Optional[str] = None
        data_buf: str = ""

        for raw_line in raw_response.iter_lines(decode_unicode=True):
            line = raw_line
            if line == "":
                if data_buf:
                    try:
                        payload_dict = json.loads(data_buf)
                    except json.JSONDecodeError:
                        data_buf = ""
                        event_name = None
                        continue
                    maybe_resp = _handle_payload(event_name, payload_dict)
                    if maybe_resp is not None:
                        raw_response.close()
                        return maybe_resp
                # reset after event
                data_buf = ""
                event_name = None
                continue

            if line.startswith("event:"):
                event_name = line[len("event:") :].strip()
            elif line.startswith("data:"):
                data_buf += line[len("data:") :].strip()

        # Process any remaining buffer (in case stream closed without blank line)
        if data_buf:
            try:
                payload_dict = json.loads(data_buf)
                maybe_resp = _handle_payload(event_name, payload_dict)
                if maybe_resp is not None:
                    raw_response.close()
                    return maybe_resp
            except json.JSONDecodeError:
                pass

        raise RuntimeError("Stream ended before completion of research task")

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
        """Async variant mirroring the synchronous implementation above."""

        import json

        payload = {
            "input": {"instructions": input_instructions},
            "output": {"schema": output_schema},
        }

        raw_response = await self._client.async_request(
            "/research/tasks", payload, force_stream=True
        )

        async def _handle_payload_async(
            tag: Optional[str], payload_dict: Dict[str, Any]
        ):
            if tag is None:
                tag_local = payload_dict.get("tag")
            else:
                tag_local = tag

            if tag_local == "progress":
                return None
            if tag_local == "error":
                msg = payload_dict.get("error", {}).get("message", "Unknown error")
                raise RuntimeError(f"Research task failed: {msg}")
            if tag_local == "complete":
                data_obj = payload_dict.get("data")
                if data_obj is None:
                    raise RuntimeError("Malformed 'complete' chunk with no data")
                return _parse_research_response(data_obj)
            if {"id", "status"}.issubset(payload_dict.keys()):
                return _parse_research_response(payload_dict)
            return None

        event_name: Optional[str] = None
        data_buf: str = ""

        async for line in raw_response.aiter_lines():
            if line == "":
                if data_buf:
                    try:
                        payload_dict = json.loads(data_buf)
                    except json.JSONDecodeError:
                        data_buf = ""
                        event_name = None
                        continue
                    maybe_resp = await _handle_payload_async(event_name, payload_dict)
                    if maybe_resp is not None:
                        await raw_response.aclose()
                        return maybe_resp
                data_buf = ""
                event_name = None
                continue

            if line.startswith("event:"):
                event_name = line[len("event:") :].strip()
            elif line.startswith("data:"):
                data_buf += line[len("data:") :].strip()

        if data_buf:
            try:
                payload_dict = json.loads(data_buf)
                maybe_resp = await _handle_payload_async(event_name, payload_dict)
                if maybe_resp is not None:
                    await raw_response.aclose()
                    return maybe_resp
            except json.JSONDecodeError:
                pass

        raise RuntimeError("Stream ended before completion of research task")

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
    from .models import ResearchTaskResponse
    from ..api import _Result, to_snake_case

    return ResearchTaskResponse(
        id=raw["id"],
        status=raw["status"],
        output=raw.get("output"),
        citations={
            key: [_Result(**to_snake_case(c)) for c in citations]
            for key, citations in raw.get("citations", {}).items()
        },
    )
