import collections.abc
import copy
import dataclasses
import functools
import operator
import types
from collections.abc import Callable
from typing import (
    Any,
    Literal,
    TypeAliasType,
    Union,
    get_args,
    get_origin,
    is_typeddict,
)

from omegaconf import MISSING

from .annotation import is_mapping_type, is_sequence_type, split_union
from .field import classify_fields
from .schema import Schema


# OmegaConf 2.3 supports neither `Literal`, nor unions with non-scalar members, nor
# fixed-length tuples, so it validates against a derived structure that holds plain
# types there. The rest is checked after OmegaConf, and building constructs the
# schema's own classes, so every supported OmegaConf version behaves the same.
@functools.cache
def derive_structure(schema: Schema) -> type:
    """Derive the dataclass that OmegaConf validates the data fields of a schema with.

    Args:
        schema: The schema to derive the structure from.

    Returns:
        A dataclass with the data fields of `schema`, whose annotations OmegaConf
        supports.
    """
    fields = classify_fields(schema)
    structure = []
    for field in dataclasses.fields(schema):
        if field.name not in fields or fields[field.name][0] != "data":
            continue
        field_type = derive_structure_type(fields[field.name][1])
        if field.default_factory is not dataclasses.MISSING:
            default = dataclasses.field(
                default_factory=functools.partial(
                    _make_structure_default, field.default_factory, field_type is Any
                )
            )
        elif field.default is not dataclasses.MISSING:
            default = dataclasses.field(
                default_factory=functools.partial(
                    _make_structure_default,
                    functools.partial(copy.deepcopy, field.default),
                    field_type is Any,
                )
            )
        else:
            default = dataclasses.field(default=MISSING)
        structure.append((field.name, field_type, default))
    return dataclasses.make_dataclass(schema.__name__, structure, kw_only=True)


def derive_structure_type(annotation: Any) -> Any:
    """Translate an annotation into one that OmegaConf supports.

    Args:
        annotation: The annotation of a data field.

    Returns:
        The annotation with `Literal`, unions with non-scalar members and fixed-length
        tuples replaced by plain types, and dataclasses by their derived structure.
    """
    while isinstance(annotation, TypeAliasType):
        annotation = annotation.__value__
    if annotation is collections.abc.Sequence:
        return list
    if annotation is collections.abc.Mapping:
        return dict
    origin = get_origin(annotation)
    arguments = get_args(annotation)
    if origin is Literal:
        return functools.reduce(
            operator.or_, dict.fromkeys(type(value) for value in arguments)
        )
    if origin in (Union, types.UnionType):
        members, _ = split_union(annotation)
        if len(members) == 1:
            return derive_structure_type(members[0]) | None
        if any(
            is_mapping_type(member) or is_sequence_type(member) for member in arguments
        ):
            return Any
        return functools.reduce(operator.or_, map(derive_structure_type, arguments))
    if origin in (list, collections.abc.Sequence) or (
        origin is tuple and len(arguments) == 2 and arguments[1] is Ellipsis
    ):
        return list[derive_structure_type(arguments[0])]
    if origin is tuple:
        return Any
    if origin in (dict, collections.abc.Mapping):
        return dict[arguments[0], derive_structure_type(arguments[1])]
    if isinstance(annotation, type) and is_typeddict(annotation):
        return dict
    if isinstance(annotation, type) and dataclasses.is_dataclass(annotation):
        return derive_structure(annotation)
    return annotation


def _make_structure_default(factory: Callable[[], Any], plain: bool) -> Any:
    return _to_structure(factory(), plain)


def _to_structure(value: Any, plain: bool) -> Any:
    # A field that is `Any` in the structure takes plain containers: a dataclass
    # default there would stay typed and reject other union members.
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        items = {
            name: _to_structure(getattr(value, name), plain)
            for name in classify_fields(type(value))
        }
        return items if plain else derive_structure(type(value))(**items)
    if isinstance(value, (list, tuple)):
        return [_to_structure(item, plain) for item in value]
    if isinstance(value, dict):
        return {key: _to_structure(item, plain) for key, item in value.items()}
    return value
