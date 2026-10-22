"""Every enum and tagged union exa-py reads from an API response stays open.

The API adds enum values and union variants without a version bump, and
callers pin SDK versions, so a closed enum on a response model turns a server
addition into a ``ValidationError`` for every installed release. This test
walks every pydantic model in ``exa_py`` and fails on:

- a field with a closed ``Literal`` of two or more values, or an ``Enum``,
  not unioned with ``str``;
- a field typed as a union of models that has no fallback for an unknown tag
  (see ``exa_py._open_union``).

Request models are exempt: the SDK sends those values and the API validates
them. So are the few response sets that are closed by definition, listed in
``CLOSED_BY_DEFINITION`` with the reason.
"""

from __future__ import annotations

import enum
import importlib
import inspect
import pkgutil
import re
import types
import typing
from typing import Any, Dict, Iterator, List, Tuple, Type

import pydantic
import pytest
from pydantic import Discriminator, Tag, TypeAdapter

import exa_py
from exa_py._open_union import UNKNOWN_TAG

REQUEST_MODEL_NAME = re.compile(r"(Params|Param|Parameters\w*|RequestDto)$")
"""Models whose name marks them as request bodies."""

REQUEST_MODELS = {
    "RequestOptions",  # websets per-request options
    "UpdateMonitor",  # websets PATCH /monitors/{id} body
}
"""Request bodies whose name the pattern above does not catch."""

CLOSED_BY_DEFINITION: Dict[Tuple[str, str], str] = {
    ("WebsetItemEvaluation", "satisfied"): "yes, no and unclear cover every answer",
    ("WebsetSearch", "behavior"): "a search either overrides or appends",
    ("MonitorBehaviorSearchConfig", "behavior"): "a search either overrides or appends",
}


def _exa_models() -> List[Type[pydantic.BaseModel]]:
    models: Dict[str, Type[pydantic.BaseModel]] = {}
    for module_info in pkgutil.walk_packages(exa_py.__path__, "exa_py."):
        module = importlib.import_module(module_info.name)
        for obj in vars(module).values():
            if (
                inspect.isclass(obj)
                and issubclass(obj, pydantic.BaseModel)
                and obj.__module__.startswith("exa_py")
            ):
                models[f"{obj.__module__}.{obj.__qualname__}"] = obj
    for model in models.values():
        model.model_rebuild()
    return [models[k] for k in sorted(models)]


def _is_request_model(model: Type[pydantic.BaseModel]) -> bool:
    return model.__name__ in REQUEST_MODELS or bool(REQUEST_MODEL_NAME.search(model.__name__))


def _declared_by_exa(model: Type[pydantic.BaseModel], field_name: str) -> bool:
    """Whether ``field_name`` is declared by an exa_py class, not inherited from a third-party model."""
    for klass in model.__mro__:
        if field_name in getattr(klass, "__annotations__", {}):
            return klass.__module__.startswith("exa_py")
    return True


def _is_union(tp: Any) -> bool:
    return typing.get_origin(tp) in (typing.Union, getattr(types, "UnionType", None))


def _closed_enums(tp: Any) -> Iterator[List[str]]:
    """Value lists of closed enums reachable in ``tp``. A union that admits ``str`` is open."""
    origin = typing.get_origin(tp)
    args = typing.get_args(tp)
    if origin is typing.Annotated:
        yield from _closed_enums(args[0])
        return
    if origin is typing.Literal:
        values = [a for a in args if isinstance(a, str)]
        if len(values) >= 2:
            yield values
        return
    if inspect.isclass(tp) and issubclass(tp, enum.Enum):
        yield [member.value for member in tp]
        return
    if _is_union(tp) and str in args:
        return
    for arg in args:
        yield from _closed_enums(arg)


def _model_unions(tp: Any, metadata: Tuple[Any, ...] = ()) -> Iterator[Tuple[Tuple[Any, ...], Tuple[Any, ...]]]:
    """Unions of two or more models reachable in ``tp``, each with its ``Annotated`` metadata."""
    origin = typing.get_origin(tp)
    args = typing.get_args(tp)
    if origin is typing.Annotated:
        yield from _model_unions(args[0], tuple(tp.__metadata__))
        return
    if _is_union(tp):
        members = [typing.get_args(a)[0] if typing.get_origin(a) is typing.Annotated else a for a in args]
        if sum(1 for m in members if inspect.isclass(m) and issubclass(m, pydantic.BaseModel)) >= 2:
            yield args, metadata
            return
    for arg in args:
        yield from _model_unions(arg)


def _has_unknown_fallback(members: Tuple[Any, ...], metadata: Tuple[Any, ...]) -> bool:
    if not any(isinstance(m, Discriminator) for m in metadata):
        return False
    return any(
        typing.get_origin(member) is typing.Annotated
        and any(isinstance(m, Tag) and m.tag == UNKNOWN_TAG for m in member.__metadata__)
        for member in members
    )


MODELS = _exa_models()


def _response_fields() -> Iterator[Tuple[str, str, Any]]:
    for model in MODELS:
        if _is_request_model(model):
            continue
        for name, field in model.model_fields.items():
            if not _declared_by_exa(model, name):
                continue
            yield model.__name__, field.alias or name, field


def test_walk_finds_the_response_models():
    names = {model.__name__ for model in MODELS}
    assert {"AgentRun", "SearchMonitorRun", "Webset", "WebsetItem", "ListEventsResponse"} <= names


def test_no_closed_enum_on_a_response_model():
    closed = [
        f"{model}.{field_name} {values}"
        for model, field_name, field in _response_fields()
        if (model, field_name) not in CLOSED_BY_DEFINITION
        for values in _closed_enums(field.annotation)
    ]
    assert closed == [], (
        "Response fields must accept values the SDK does not list: type them "
        "Union[Known..., str]. Closed enums found:\n" + "\n".join(closed)
    )


def test_every_response_union_of_models_has_an_unknown_fallback():
    closed = [
        f"{model}.{field_name}"
        for model, field_name, field in _response_fields()
        for members, metadata in _model_unions(field.annotation, tuple(field.metadata))
        if not _has_unknown_fallback(members, metadata)
    ]
    assert closed == [], (
        "Response unions must route an unknown tag to a fallback model: see "
        "exa_py._open_union. Closed unions found:\n" + "\n".join(closed)
    )


def _is_fallback(member: Any) -> bool:
    return any(isinstance(m, Tag) and m.tag == UNKNOWN_TAG for m in getattr(member, "__metadata__", ()))


def _aliases(model: Type[pydantic.BaseModel], *, required: bool = False) -> set:
    return {f.alias or n for n, f in model.model_fields.items() if f.is_required() or not required}


def test_every_unknown_fallback_declares_the_fields_its_variants_share():
    """A field every known variant has is on the fallback too, and required where they all require it.

    Otherwise reading it off the union (``item.properties.url``,
    ``event.created_at``) stops type-checking once the fallback joins the union.
    """
    gaps = []
    for model, field_name, field in _response_fields():
        for members, metadata in _model_unions(field.annotation, tuple(field.metadata)):
            if not _has_unknown_fallback(members, metadata):
                continue
            known = [typing.get_args(m)[0] for m in members if not _is_fallback(m)]
            fallback = next(typing.get_args(m)[0] for m in members if _is_fallback(m))
            shared = set.intersection(*(_aliases(k) for k in known))
            shared_required = set.intersection(*(_aliases(k, required=True) for k in known))
            missing = sorted(shared - _aliases(fallback))
            optional = sorted((shared_required - set(missing)) - _aliases(fallback, required=True))
            if missing or optional:
                gaps.append(f"{model}.{field_name} -> {fallback.__name__}: missing {missing}, optional {optional}")
    assert gaps == [], "Fallbacks lack fields their variants share:\n" + "\n".join(sorted(set(gaps)))


@pytest.mark.parametrize("key", sorted(CLOSED_BY_DEFINITION))
def test_closed_by_definition_entries_still_exist(key):
    model_name, field_name = key
    model = next(m for m in MODELS if m.__name__ == model_name)
    aliases = {f.alias or n for n, f in model.model_fields.items()}
    assert field_name in aliases
