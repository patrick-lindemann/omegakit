import collections.abc
import dataclasses
import functools
import types
from collections.abc import Iterator, Mapping
from typing import (
    Any,
    Literal,
    TypeAliasType,
    get_args,
    get_origin,
    get_type_hints,
)

from omegaconf import OmegaConf
from omegaconf.errors import OmegaConfBaseException

from omegakit.core.errors import SchemaDefinitionError
from omegakit.core.utils import describe_error

from .annotation import split_union
from .schema import Schema

type _FieldKind = Literal["data", "object", "any"]


@functools.cache
def classify_fields(schema: Schema) -> Mapping[str, tuple[_FieldKind, Any]]:
    """Classify the configurable fields of a schema.

    A field is `any` for `Any`, `data` if OmegaConf accepts its annotation, and
    `object` if the annotation is built only from classes that OmegaConf does not
    accept.

    Args:
        schema: The schema whose fields are classified.

    Returns:
        The kind and resolved annotation of every configurable field, by field name,
        read-only because the result is cached.

    Raises:
        SchemaDefinitionError: If an annotation does not resolve, or OmegaConf
            rejects it and it is not built from classes.
    """
    try:
        hints = get_type_hints(schema)
    # Evaluating an annotation runs arbitrary code, which can raise anything.
    except Exception as error:
        raise SchemaDefinitionError(
            f"Cannot resolve the annotations of schema `{schema.__qualname__}`: "
            f"{describe_error(error)}"
        ) from error
    return types.MappingProxyType(
        {
            field.name: (
                _classify_field(hints[field.name], schema, field.name),
                hints[field.name],
            )
            for field in dataclasses.fields(schema)
            if field.init
        }
    )


def _classify_field(annotation: Any, schema: Schema, name: str) -> _FieldKind:
    if annotation is Any:
        return "any"
    objection = _find_omegaconf_objection(annotation)
    if objection is None:
        return "data"
    if _is_object(annotation):
        return "object"
    raise SchemaDefinitionError(
        f"Field `{name}` of schema `{schema.__qualname__}` has `{annotation}`, which "
        f"OmegaConf does not support: {objection}"
    )


@functools.cache
def _find_omegaconf_objection(
    annotation: Any, visited: frozenset[type] = frozenset()
) -> str | None:
    try:
        OmegaConf.structured(
            dataclasses.make_dataclass("Field", [("value", annotation)])
        )
    except OmegaConfBaseException as error:
        return describe_error(error)
    # OmegaConf checks the fields of a nested dataclass only when a value arrives.
    for schema in _find_dataclasses(annotation):
        if schema in visited:
            continue
        try:
            hints = get_type_hints(schema)
        except Exception as error:
            return describe_error(error)
        for field in dataclasses.fields(schema):
            objection = _find_omegaconf_objection(hints[field.name], visited | {schema})
            if objection is not None:
                return objection
    return None


def _find_dataclasses(annotation: Any) -> Iterator[type]:
    while isinstance(annotation, TypeAliasType):
        annotation = annotation.__value__
    if isinstance(annotation, type) and dataclasses.is_dataclass(annotation):
        yield annotation
    for argument in get_args(annotation):
        yield from _find_dataclasses(argument)


def _is_object(annotation: Any) -> bool:
    members, _ = split_union(annotation)
    return all(_is_object_member(member) for member in members)


def _is_object_member(member: Any) -> bool:
    while isinstance(member, TypeAliasType):
        member = member.__value__
    origin = get_origin(member)
    if origin in (list, dict):
        arguments = get_args(member)
        return bool(arguments) and _is_object(arguments[-1])
    cls = member if origin is None else origin
    return (
        isinstance(cls, type)
        and cls not in (tuple, set, frozenset)
        and (cls.__module__ != "collections.abc" or cls is collections.abc.Callable)
        and _find_omegaconf_objection(member) is not None
    )
