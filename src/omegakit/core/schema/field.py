import collections.abc
import dataclasses
import enum
import functools
import sys
import types
from collections.abc import Mapping
from pathlib import Path
from typing import (
    Any,
    Literal,
    TypeAliasType,
    Union,
    get_args,
    get_origin,
    get_type_hints,
    is_typeddict,
)

from omegakit.core.errors import SchemaDefinitionError
from omegakit.core.utils import describe_error

from .annotation import is_mapping_type, is_sequence_type, split_union
from .schema import Schema

type _FieldKind = Literal["data", "object", "any"]

_SCALAR_TYPES = (int, float, bool, str, bytes, Path)
_UNSUPPORTED_CONTAINERS = (
    set,
    frozenset,
    collections.abc.Iterable,
    collections.abc.Collection,
    collections.abc.MutableSequence,
    collections.abc.Set,
    collections.abc.MutableSet,
    collections.abc.MutableMapping,
)


@functools.cache
def classify_fields(
    schema: Schema, outer: tuple[Schema, ...] = ()
) -> Mapping[str, tuple[_FieldKind, Any]]:
    """Classify the configurable fields of a schema.

    Args:
        schema: The schema whose fields are classified.
        outer: The dataclasses whose fields lead to `schema`, outermost first.
            Defaults to `()`.

    Returns:
        The kind and resolved annotation of every configurable field, by field name,
        read-only because the result is cached.

    Raises:
        SchemaDefinitionError: If the schema uses a dataclass feature outside the
            supported subset, or contains itself.
    """
    if schema in outer:
        cycle = (*outer[outer.index(schema) :], schema)
        raise SchemaDefinitionError(
            f"Schema `{schema.__qualname__}` contains itself: "
            f"{' -> '.join(cls.__qualname__ for cls in cycle)}. Recursive schemas are "
            "not supported."
        )
    hints = _resolve_type_hints(schema)
    for name, hint in hints.items():
        if isinstance(hint, dataclasses.InitVar) and not hasattr(schema, name):
            raise SchemaDefinitionError(
                f"Field `{name}` of schema `{schema.__qualname__}` is an `InitVar` "
                "without a default, which a config cannot set. Give it a default."
            )
    return types.MappingProxyType(
        {
            field.name: (
                _classify_field(
                    hints[field.name], schema, field.name, (*outer, schema)
                ),
                hints[field.name],
            )
            for field in dataclasses.fields(schema)
            if field.init
        }
    )


def _resolve_type_hints(schema: Schema) -> dict[str, Any]:
    try:
        return get_type_hints(schema)
    except NameError as error:
        for field in dataclasses.fields(schema):
            if not isinstance(field.type, str):
                continue
            # An inherited field shares its `Field` with the base that defines it.
            owner = next(
                base
                for base in reversed(schema.__mro__)
                if getattr(base, "__dataclass_fields__", {}).get(field.name) is field
            )
            try:
                eval(
                    field.type,
                    vars(sys.modules[owner.__module__]),
                    dict(vars(owner)),
                )
            except NameError:
                raise SchemaDefinitionError(
                    f"Cannot resolve the annotation of field `{field.name}` of schema "
                    f"`{schema.__qualname__}`: {error}. Import the type at module "
                    "level, not under `TYPE_CHECKING` or inside a function."
                ) from error
        raise SchemaDefinitionError(
            f"Cannot resolve the annotations of schema `{schema.__qualname__}`: "
            f"{error}."
        ) from error
    # Evaluating an annotation runs arbitrary code, which can raise anything.
    except Exception as error:
        raise SchemaDefinitionError(
            f"Cannot resolve the annotations of schema `{schema.__qualname__}`: "
            f"{describe_error(error)}."
        ) from error


def _classify_field(
    annotation: Any, schema: Schema, name: str, outer: tuple[Schema, ...]
) -> _FieldKind:
    while isinstance(annotation, TypeAliasType):
        annotation = annotation.__value__
    origin = get_origin(annotation)
    arguments = get_args(annotation)
    if origin is Literal:
        if all(type(value) in (str, int, bool) for value in arguments):
            return "data"
        raise SchemaDefinitionError(
            f"Field `{name}` of schema `{schema.__qualname__}` has `{annotation}`, but "
            "`Literal` values must be strings, integers or booleans."
        )
    if annotation is Any:
        return "any"
    if annotation in _SCALAR_TYPES or (
        isinstance(annotation, type) and issubclass(annotation, enum.Enum)
    ):
        return "data"
    if isinstance(annotation, type) and dataclasses.is_dataclass(annotation):
        kinds = {kind for kind, _ in classify_fields(annotation, outer).values()}
        return "data" if kinds <= {"data"} else "object"
    if isinstance(annotation, type) and is_typeddict(annotation):
        return "data"
    if origin in (Union, types.UnionType):
        members, _ = split_union(annotation)
        member_kinds: set[_FieldKind] = {
            _classify_field(member, schema, name, outer) for member in members
        }
        if len(member_kinds) > 1:
            raise SchemaDefinitionError(
                f"Field `{name}` of schema `{schema.__qualname__}` mixes value types "
                f"and classes in `{annotation}`. Use a union of plain values, a union "
                "of classes, or `Any`."
            )
        kind = member_kinds.pop()
        if kind == "data" and (
            sum(is_mapping_type(member) for member in members) > 1
            or sum(is_sequence_type(member) for member in members) > 1
        ):
            raise SchemaDefinitionError(
                f"Field `{name}` of schema `{schema.__qualname__}` has `{annotation}`, "
                "whose mapping or list members cannot be told apart. Use at most one "
                "mapping type and one list type in a union, or `Any`."
            )
        return kind
    if annotation in (
        list,
        dict,
        tuple,
        collections.abc.Sequence,
        collections.abc.Mapping,
    ) or origin in (
        list,
        dict,
        tuple,
        collections.abc.Sequence,
        collections.abc.Mapping,
    ):
        items = [argument for argument in arguments if argument is not Ellipsis]
        if origin is dict or origin is collections.abc.Mapping:
            items = items[1:]
        kinds: set[_FieldKind] = {
            _classify_field(item, schema, name, outer) for item in items
        }
        if kinds <= {"data"}:
            return "data"
        if kinds == {"object"} and origin in (list, dict):
            return "object"
        if kinds == {"any"}:
            return "any"
        raise SchemaDefinitionError(
            f"Field `{name}` of schema `{schema.__qualname__}` has `{annotation}`, "
            "but a container can hold either plain values or objects, and objects "
            "only in `list` and `dict`. Use `Any` otherwise."
        )
    if annotation in _UNSUPPORTED_CONTAINERS or origin in _UNSUPPORTED_CONTAINERS:
        raise SchemaDefinitionError(
            f"Field `{name}` of schema `{schema.__qualname__}` has the unsupported "
            f"container `{annotation}`. Use `list`, `dict`, `tuple` or `Any`."
        )
    if origin is None and isinstance(annotation, type):
        return "object"
    if isinstance(origin, type):
        return "object"
    raise SchemaDefinitionError(
        f"Field `{name}` of schema `{schema.__qualname__}` has the unsupported "
        f"annotation `{annotation}`."
    )
