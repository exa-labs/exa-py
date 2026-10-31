"""Every public name an earlier release exported is still importable from the same module.

``fixtures/public_names_2.26.0.json`` lists, per module, the classes and
functions exa_py defined and the type aliases it bound in release 2.26.0,
including names a module only re-imported (``from exa_py.websets.events.client
import WebsetCreatedEvent`` is user code too). Removing one breaks code
written against that release, so it needs a major release and an update of
the fixture.

Regenerate the fixture from a published release with::

    uv run --no-project --with 'exa-py==<version>' python tests/unit/test_public_names.py \
        > tests/unit/fixtures/public_names_<version>.json
"""

from __future__ import annotations

import importlib
import inspect
import json
import pkgutil
import sys
import typing
from pathlib import Path
from typing import Dict, List

import typing_extensions

BASELINE = Path(__file__).parent / "fixtures" / "public_names_2.26.0.json"

ALIAS_ORIGINS = {
    typing.Union,
    typing.Literal,
    typing.Annotated,
    # Distinct objects on Python versions where typing_extensions backports them.
    typing_extensions.Literal,
    typing_extensions.Annotated,
}


def _is_public(obj: object) -> bool:
    """A class or function exa_py defines, or a type alias such as ``Literal[...]`` or ``Union[...]``."""
    if inspect.isclass(obj) or inspect.isfunction(obj):
        return getattr(obj, "__module__", "").startswith("exa_py")
    return typing_extensions.get_origin(obj) in ALIAS_ORIGINS


def public_names() -> Dict[str, List[str]]:
    """Public names of every non-private module of the installed exa_py."""
    import exa_py

    names: Dict[str, List[str]] = {}
    for info in sorted(pkgutil.walk_packages(exa_py.__path__, "exa_py."), key=lambda i: i.name):
        if any(part.startswith("_") for part in info.name.split(".")[1:]):
            continue
        module = importlib.import_module(info.name)
        found = sorted(n for n, o in vars(module).items() if not n.startswith("_") and _is_public(o))
        if found:
            names[info.name] = found
    return names


def test_every_name_of_the_baseline_release_is_still_importable():
    """Checks importability alone, so how a name's type is spelled on this Python version does not matter."""
    baseline = json.loads(BASELINE.read_text())
    missing = [
        f"from {module} import {name}"
        for module, names in baseline.items()
        for name in names
        if not hasattr(importlib.import_module(module), name)
    ]
    assert missing == [], "Names earlier releases exported are gone:\n" + "\n".join(missing)


if __name__ == "__main__":
    json.dump(public_names(), sys.stdout, indent=1, sort_keys=True)
    sys.stdout.write("\n")
