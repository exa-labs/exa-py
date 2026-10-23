"""Tagged unions that keep a variant the SDK does not know.

A response union is tagged by one field (``type``, ``status``, ``eventType``,
...). Each union is written as::

    Annotated[
        Union[
            Annotated[KnownA, Tag("a")],
            Annotated[KnownB, Tag("b")],
            Annotated[UnknownFallback, Tag(UNKNOWN_TAG)],
        ],
        tag_discriminator("type", KnownA, KnownB),
    ]

``tag_discriminator`` routes each tag a variant declares to that variant and
every other tag to the fallback, which keeps the whole payload. A variant the
API adds later then parses instead of failing validation, and a payload whose
tag is known is still validated strictly against its variant. Each ``Tag`` is
the value of its variant's ``Literal`` tag field.
"""

from __future__ import annotations

import typing
from typing import Any, FrozenSet, Type

from pydantic import BaseModel, Discriminator

UNKNOWN_TAG = "__unknown__"
"""Tag of the fallback variant. Never a value the API sends."""


def _declared_tag(model: Type[BaseModel], field_name: str) -> str:
    """The single string a variant's ``Literal`` tag field accepts."""
    annotation = model.model_fields[field_name].annotation
    values = typing.get_args(annotation)
    if typing.get_origin(annotation) is not typing.Literal or len(values) != 1:
        raise TypeError(
            f"{model.__name__}.{field_name} must be a Literal of one value to tag a union"
        )
    return values[0]


def tag_discriminator(field_name: str, *variants: Type[BaseModel]) -> Discriminator:
    """Route a payload by its ``field_name`` tag: a tag one of ``variants`` declares, else ``UNKNOWN_TAG``.

    ``field_name`` is the Python attribute name. The wire alias is read from
    the first variant's field, so payloads using either name are routed.
    """
    known: FrozenSet[str] = frozenset(
        _declared_tag(variant, field_name) for variant in variants
    )
    alias = variants[0].model_fields[field_name].alias or field_name

    def discriminate(value: Any) -> str:
        if isinstance(value, dict):
            tag = value.get(alias, value.get(field_name))
        else:
            tag = getattr(value, field_name, None)
        return tag if tag in known else UNKNOWN_TAG

    return Discriminator(discriminate)
