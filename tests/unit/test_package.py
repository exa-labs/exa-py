"""The installed package: what it exports, what it reports, and that it imports."""

import importlib
import importlib.metadata
import inspect
import pkgutil
import sys
import typing
from pathlib import Path
from typing import get_type_hints
from unittest.mock import patch

import pytest

import exa_py
from exa_py import AsyncExa, Exa
from exa_py.utils import _get_package_version


def test_user_agent_reports_the_installed_version():
    with patch("exa_py.utils.importlib.metadata.version", return_value="9.8.7") as version:
        assert Exa("test-key").headers["User-Agent"] == "exa-py/9.8.7"
        assert AsyncExa("test-key").headers["User-Agent"] == "exa-py/9.8.7"
    version.assert_called_with("exa-py")


def test_a_source_checkout_that_is_not_installed_reads_its_pyproject():
    tomllib = pytest.importorskip("tomllib")
    pyproject = Path(exa_py.__file__).resolve().parent.parent / "pyproject.toml"
    if not pyproject.exists():
        pytest.skip("not a source checkout")
    expected = tomllib.loads(pyproject.read_text())["project"]["version"]
    with patch(
        "exa_py.utils.importlib.metadata.version",
        side_effect=importlib.metadata.PackageNotFoundError("exa-py"),
    ):
        assert _get_package_version() == expected


def test_a_custom_user_agent_is_kept():
    assert Exa("test-key", user_agent="my-app/1.0").headers["User-Agent"] == "my-app/1.0"


def test_the_user_location_types_are_exported_from_the_package():
    from exa_py import UserLocation, UserLocationCoordinates, UserLocationCountry
    from exa_py import api

    assert UserLocation is api.UserLocation
    assert UserLocationCountry is api.UserLocationCountry
    assert UserLocationCoordinates is api.UserLocationCoordinates


def test_every_module_of_the_package_imports():
    names = [module.name for module in pkgutil.walk_packages(exa_py.__path__, "exa_py.")]
    assert names
    for name in names:
        importlib.import_module(name)


@pytest.mark.skipif(sys.version_info < (3, 11), reason="typing.get_overloads needs Python 3.11")
@pytest.mark.parametrize("client", [Exa, AsyncExa])
def test_get_contents_overloads_take_every_content_option_the_method_accepts(client):
    # Type checkers pick from the overloads alone, so one must take each content
    # option the method accepts at runtime, False included.
    signatures = [
        inspect.signature(o, eval_str=True) for o in typing.get_overloads(client.get_contents)
    ]
    for option in ("text", "summary", "highlights", "metadata", "context"):
        assert any(
            option in s.parameters and bool in typing.get_args(s.parameters[option].annotation)
            for s in signatures
        ), option


def test_async_client_attributes_are_declared_with_the_types_they_hold():
    exa = AsyncExa("test-key")
    hints = get_type_hints(AsyncExa)
    for name in ("research", "websets", "monitors", "agent", "beta", "tools", "openai", "anthropic"):
        assert type(getattr(exa, name)) is hints[name], name
