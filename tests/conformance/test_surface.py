"""Stable public-surface and endpoint-coverage snapshots."""

from __future__ import annotations

import csv
import importlib
import inspect
import json
import pkgutil
import re
from pathlib import Path
from typing import Any

import exa_py

from .conftest import read_json_lines, write_or_compare
from .test_requests import _evaluated_signature, _resolve

ROOT = Path(__file__).parent
INVENTORY = ROOT / "exa-py-surface.tsv"
ENDPOINT_INVENTORY = ROOT / "endpoint-coverage.tsv"
REQUEST_GOLDEN = ROOT / "goldens" / "requests.json"
GOLDEN = ROOT / "goldens" / "signatures.jsonl"


def _modules() -> list[Any]:
    modules = [exa_py]
    for info in pkgutil.walk_packages(exa_py.__path__, exa_py.__name__ + "."):
        try:
            modules.append(importlib.import_module(info.name))
        except ImportError:
            continue
    return modules


def _callable_rows() -> list[dict[str, str]]:
    with INVENTORY.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _signature_without_self(signature: str) -> str:
    return signature.replace("(self, ", "(", 1).replace("(self)", "()", 1)


def _normalize_signature(signature: str) -> str:
    signature = signature.replace("NoneType", "None")
    signature = signature.replace("pathlib._local.Path", "pathlib.Path")
    signature = re.sub(
        r"Annotated\[(Union\[.*?\]), "
        r"FieldInfo\(annotation=None, required=True, discriminator='status'\)\]",
        r"\1",
        signature,
    )
    while "Union[Union[" in signature:
        start = signature.index("Union[Union[")
        nested_start = start + len("Union[")
        depth = 0
        nested_end = None
        for index in range(nested_start, len(signature)):
            if signature[index] == "[":
                depth += 1
            elif signature[index] == "]":
                depth -= 1
                if depth == 0:
                    nested_end = index
                    break
        if nested_end is None or signature[nested_end + 1 : nested_end + 3] != ", ":
            break
        outer_depth = 0
        outer_end = None
        for index in range(start, len(signature)):
            if signature[index] == "[":
                outer_depth += 1
            elif signature[index] == "]":
                outer_depth -= 1
                if outer_depth == 0:
                    outer_end = index
                    break
        if outer_end is None:
            break
        nested = signature[nested_start : nested_end + 1]
        rest = signature[nested_end + 3 : outer_end]
        signature = (
            signature[:start]
            + "Union["
            + nested[len("Union[") : -1]
            + ", "
            + rest
            + "]"
            + signature[outer_end + 1 :]
        )
    return signature


def _live_method(client: Any, row: dict[str, str]) -> Any:
    """Resolve an inventory row to the live client attribute."""
    if row["http_endpoint"] != "n/a":
        method = _resolve(
            client, row["namespace"], row["method"], row["http_endpoint"]
        )
        assert method is not None, (
            f'live callable missing: {row["namespace"]}.{row["method"]} '
            f'({row["source_file:line"]})'
        )
        return method
    namespace = row["namespace"].split(".")[1:]
    roots = [client]
    if namespace[:2] == ["agent", "monitors"]:
        roots = [client.beta]
    for root in roots:
        try:
            values = [root]
            for part in namespace:
                values = [getattr(value, part) for value in values]
            descriptor = inspect.getattr_static(values[0], row["method"])
            return descriptor if isinstance(descriptor, property) else getattr(
                values[0], row["method"]
            )
        except AttributeError:
            if namespace == ["agent", "monitors"] and row["method"] in {
                "poll_until_finished",
                "create_and_wait",
            }:
                return getattr(values[0].snapshots, row["method"])
    source = Path(row["source_file:line"].rsplit(":", 1)[0])
    source_text = source.as_posix()
    package_index = source_text.index("/exa_py/")
    relative = Path(source_text[package_index + 1 :]).with_suffix("")
    module = importlib.import_module(".".join(relative.parts))
    line = int(row["source_file:line"].rsplit(":", 1)[1])
    for _, value in inspect.getmembers(module, inspect.isclass):
        method = inspect.getattr_static(value, row["method"], None)
        if method is None:
            continue
        candidate = method.__func__ if isinstance(method, (staticmethod, classmethod)) else method
        try:
            first_line = inspect.getsourcelines(candidate)[1]
        except (OSError, TypeError):
            continue
        if abs(first_line - line) <= 2:
            return getattr(value, row["method"])
    raise AssertionError(
        f'live callable missing: {row["namespace"]}.{row["method"]} '
        f'({row["source_file:line"]})'
    )


def _live_signature(method: Any) -> str:
    if isinstance(method, property):
        method = method.fget
    assert method is not None
    return _normalize_signature(
        _signature_without_self(str(_evaluated_signature(method)))
    )


def _snapshot() -> list[dict[str, str]]:
    records = []
    for row in _callable_rows():
        client = (
            exa_py.AsyncExa(api_key="dummy-api-key")
            if row["namespace"].startswith("AsyncExa")
            else exa_py.Exa(api_key="dummy-api-key")
        )
        method = _live_method(client, row)
        records.append(
            {
                "name": f'{row["namespace"]}.{row["method"]}',
                "signature": _live_signature(method),
            }
        )
    return records


def test_public_surface_snapshot() -> None:
    """Record or compare inspect-derived public symbols and model fields."""
    write_or_compare(GOLDEN, _snapshot())


def test_inventory_endpoint_coverage() -> None:
    """Ensure every vendored SDK-side endpoint has a corpus row."""
    expected: set[tuple[str, str]] = set()
    with ENDPOINT_INVENTORY.open(newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            if row["exa_py_methods"] in {"", "NONE"}:
                continue
            expected.add((row["method"], row["path"]))
    corpus = read_json_lines(REQUEST_GOLDEN)
    actual = {
        (request["method"], request["url"].split("/api.exa.ai", 1)[-1].split("?", 1)[0])
        for request in corpus
    }

    def covered(endpoint: tuple[str, str]) -> bool:
        method, expected_path = endpoint
        for actual_method, actual_path in actual:
            if method != actual_method:
                continue
            expected_parts = expected_path.strip("/").split("/")
            actual_parts = actual_path.strip("/").split("/")
            if len(expected_parts) == len(actual_parts) and all(
                expected_part.startswith("{")
                or expected_part == actual_part
                for expected_part, actual_part in zip(expected_parts, actual_parts)
            ):
                return True
        return False

    missing = sorted(endpoint for endpoint in expected if not covered(endpoint))
    assert not missing, f"missing SDK endpoints: {missing}"
