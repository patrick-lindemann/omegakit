import collections.abc
import dataclasses
import enum
import functools
import types
from pathlib import Path
from typing import Any, Literal, TypeAliasType, Union, cast, get_args, get_origin

from omegaconf import MISSING, OmegaConf
from omegaconf.errors import MissingMandatoryValue, OmegaConfBaseException

from omegakit.core.errors import (
    ConfigValidationError,
    OmegaKitBaseException,
    SchemaDefinitionError,
)
from omegakit.core.utils import (
    describe_error,
    describe_value,
    format_full_key,
    format_path,
)

from .annotation import is_mapping_type, is_sequence_type, split_union
from .field import classify_fields
from .schema import Schema
from .structure import derive_structure, derive_structure_type


def coerce_fields(
    schema: Schema,
    values: dict[str, Any],
    path: tuple[str | int, ...],
    allow_missing: bool = False,
    build: bool = False,
) -> dict[str, Any]:
    """Validate and coerce the data fields of a node through OmegaConf.

    Args:
        schema: The schema of the node.
        values: The node's resolved values, without `$` keys.
        path: The node's path from the config root.
        allow_missing: Keep missing values as `???` instead of raising, including
            required fields that are not given. Defaults to `False`.
        build: Construct the nested dataclasses of data fields. Without it, their
            fields are checked and kept as mappings. Defaults to `False`.

    Returns:
        The coerced data fields. Absent fields with a default are left out, so
        that the dataclass fills them in itself.

    Raises:
        ConfigValidationError: If a key is not a field, a required field is missing,
            or a data value does not match its annotation.
        SchemaDefinitionError: If OmegaConf cannot validate the schema's fields.
    """  # noqa: DOC503
    fields = classify_fields(schema)
    location = f"`{format_path(path)}` ({schema.__qualname__})"
    unknown = [key for key in values if key not in fields]
    if unknown:
        raise ConfigValidationError(
            f"Unknown field(s) {', '.join(f'`{key}`' for key in unknown)} in "
            f"{location}. Expected one of {', '.join(f'`{name}`' for name in fields)}."
        )
    for name, (kind, _) in fields.items():
        if (
            not allow_missing
            and kind != "data"
            and name not in values
            and name not in _find_defaulted_fields(schema)
        ):
            raise ConfigValidationError(
                f"Missing required field `{name}` in {location}."
            )
    data = {
        key: _normalize_enums(value, fields[key][1])
        for key, value in values.items()
        if fields[key][0] == "data"
    }
    try:
        structure = OmegaConf.structured(derive_structure(schema))
    except OmegaKitBaseException:
        raise
    except OmegaConfBaseException as error:
        raise SchemaDefinitionError(
            f"Schema `{schema.__qualname__}` cannot be validated by OmegaConf: "
            f"{describe_error(error)}"
        ) from error
    try:
        merged = OmegaConf.to_container(
            OmegaConf.merge(structure, data),
            resolve=True,
            throw_on_missing=not allow_missing,
        )
    except OmegaKitBaseException:
        raise
    except OmegaConfBaseException as error:
        if isinstance(error, MissingMandatoryValue) and error.full_key:
            raise ConfigValidationError(
                f"Missing required field `{format_full_key(error.full_key)}` in "
                f"{location}."
            ) from error
        message = describe_error(error)
        if error.full_key:
            location = (
                f"`{format_path((*path, format_full_key(error.full_key)))}` "
                f"({schema.__qualname__})"
            )
        raise ConfigValidationError(
            f"Invalid config in {location}: {message}"
        ) from error
    merged = cast(dict[str, Any], merged)
    return {
        name: _build_value(
            merged[name],
            data.get(name),
            annotation,
            (*path, name),
            allow_missing,
            build,
        )
        for name, (kind, annotation) in fields.items()
        if kind == "data"
        and (name in data or name not in _find_defaulted_fields(schema))
    }


def _normalize_enums(value: Any, annotation: Any) -> Any:
    # OmegaConf 2.3 takes enum members by name, and by value only for `int` values;
    # 2.4 also by `str` value. Names win; values are turned into names before the
    # merge, so every version accepts the same.
    while isinstance(annotation, TypeAliasType):
        annotation = annotation.__value__
    origin = get_origin(annotation)
    arguments = get_args(annotation)
    if isinstance(annotation, type) and issubclass(annotation, enum.Enum):
        if type(value) in (str, int) and value not in annotation.__members__:
            for member in annotation:
                if type(member.value) is type(value) and member.value == value:
                    return member.name
        return value
    if origin in (Union, types.UnionType):
        members, _ = split_union(annotation)
        return _normalize_enums(value, members[0]) if len(members) == 1 else value
    if origin in (list, tuple, collections.abc.Sequence) and isinstance(value, list):
        if origin is tuple and not (len(arguments) == 2 and arguments[1] is Ellipsis):
            if len(value) != len(arguments):
                return value
            return [
                _normalize_enums(item, item_annotation)
                for item, item_annotation in zip(value, arguments, strict=True)
            ]
        return [_normalize_enums(item, arguments[0]) for item in value]
    if origin in (dict, collections.abc.Mapping) and isinstance(value, dict):
        return {
            _normalize_enums(key, arguments[0]): _normalize_enums(item, arguments[1])
            for key, item in value.items()
        }
    if (
        isinstance(annotation, type)
        and dataclasses.is_dataclass(annotation)
        and isinstance(value, dict)
    ):
        fields = classify_fields(annotation)
        return {
            key: _normalize_enums(item, fields[key][1]) if key in fields else item
            for key, item in value.items()
        }
    return value


def _coerce(
    value: Any,
    annotation: Any,
    path: tuple[str | int, ...],
    allow_missing: bool,
    build: bool,
) -> Any:
    try:
        structure = OmegaConf.structured(_derive_value_structure(annotation))
    except OmegaKitBaseException:
        raise
    except OmegaConfBaseException as error:
        raise SchemaDefinitionError(
            f"`{format_path(path)}` has `{annotation}`, which OmegaConf cannot "
            f"validate: {describe_error(error)}"
        ) from error
    try:
        merged = OmegaConf.to_container(
            OmegaConf.merge(structure, {"value": _normalize_enums(value, annotation)}),
            resolve=True,
            throw_on_missing=not allow_missing,
        )
    except OmegaKitBaseException:
        raise
    except OmegaConfBaseException as error:
        # The structure holds the value in its field `value`.
        field = (error.full_key or "").removeprefix("value").lstrip(".")
        if isinstance(error, MissingMandatoryValue) and field:
            raise ConfigValidationError(
                f"Missing required field `{format_full_key(field)}` in "
                f"`{format_path(path)}`."
            ) from error
        raise ConfigValidationError(
            f"Invalid config in `{format_path(path)}`: {describe_error(error)}"
        ) from error
    return _build_value(
        cast(dict[str, Any], merged)["value"],
        value,
        annotation,
        path,
        allow_missing,
        build,
    )


@functools.cache
def _derive_value_structure(annotation: Any) -> type:
    return dataclasses.make_dataclass(
        "Value", [("value", derive_structure_type(annotation), dataclasses.field())]
    )


def _build_value(
    value: Any,
    given: Any,
    annotation: Any,
    path: tuple[str | int, ...],
    allow_missing: bool,
    build: bool,
) -> Any:
    # `given` is the value as the config gave it, before OmegaConf filled in the
    # defaults. A dataclass default is not rebuilt from its own fields, because its
    # `__post_init__` has already run on them.
    if value == MISSING:
        return value
    while isinstance(annotation, TypeAliasType):
        annotation = annotation.__value__
    origin = get_origin(annotation)
    arguments = get_args(annotation)
    if origin is Literal:
        if not _is_match(value, annotation):
            raise ConfigValidationError(
                f"`{format_path(path)}` must be one of "
                f"{', '.join(map(repr, arguments))}, but the config gives "
                f"{describe_value(value)}."
            )
        return value
    if origin in (Union, types.UnionType):
        return _build_union_value(value, given, annotation, path, allow_missing, build)
    if origin in (list, collections.abc.Sequence):
        return [
            _build_value(
                item,
                given[index] if isinstance(given, list) else None,
                arguments[0],
                (*path, index),
                allow_missing,
                build,
            )
            for index, item in enumerate(value)
        ]
    if origin is tuple and len(arguments) == 2 and arguments[1] is Ellipsis:
        return tuple(
            _build_value(
                item,
                given[index] if isinstance(given, list) else None,
                arguments[0],
                (*path, index),
                allow_missing,
                build,
            )
            for index, item in enumerate(value)
        )
    if annotation is tuple:
        return tuple(value)
    if origin is tuple:
        if not isinstance(value, (list, tuple)) or len(value) != len(arguments):
            raise ConfigValidationError(
                f"`{format_path(path)}` expects a list of {len(arguments)} items for "
                f"`{annotation}`, but the config gives {describe_value(value)}."
            )
        return tuple(
            _coerce(item, item_annotation, (*path, index), allow_missing, build)
            for index, (item, item_annotation) in enumerate(
                zip(value, arguments, strict=True)
            )
        )
    if origin in (dict, collections.abc.Mapping):
        return {
            key: _build_value(
                item,
                given.get(key) if isinstance(given, dict) else None,
                arguments[1],
                (*path, key),
                allow_missing,
                build,
            )
            for key, item in value.items()
        }
    if isinstance(annotation, type) and dataclasses.is_dataclass(annotation):
        fields = classify_fields(annotation)
        given = given if isinstance(given, dict) else value
        items = {
            name: _build_value(
                item,
                given.get(name),
                fields[name][1],
                (*path, name),
                allow_missing,
                build,
            )
            for name, item in value.items()
            if name in given or name not in _find_defaulted_fields(annotation)
        }
        return annotation(**items) if build else items
    return value


def _build_union_value(
    value: Any,
    given: Any,
    annotation: Any,
    path: tuple[str | int, ...],
    allow_missing: bool,
    build: bool,
) -> Any:
    members, optional = split_union(annotation)
    if value is None and optional:
        return None
    if len(members) == 1:
        return _build_value(value, given, members[0], path, allow_missing, build)
    if isinstance(value, dict):
        for member in members:
            if is_mapping_type(member):
                return _coerce(value, member, path, allow_missing, build)
    elif isinstance(value, (list, tuple)):
        for member in members:
            if is_sequence_type(member):
                return _coerce(value, member, path, allow_missing, build)
    elif any(_is_match(value, member) for member in members):
        return value
    raise ConfigValidationError(
        f"`{format_path(path)}` expects `{annotation}`, but the config gives "
        f"{describe_value(value)}."
    )


@functools.cache
def _find_defaulted_fields(schema: Schema) -> frozenset[str]:
    return frozenset(
        field.name
        for field in dataclasses.fields(schema)
        if field.default is not dataclasses.MISSING
        or field.default_factory is not dataclasses.MISSING
    )


def _is_match(value: Any, member: Any) -> bool:
    # Scalars in a union need the member's exact type, as in OmegaConf: `True` is not
    # an `int`, `3` is not a `float`, and a string is not a `Path` or an enum member.
    while isinstance(member, TypeAliasType):
        member = member.__value__
    if get_origin(member) is Literal:
        return any(
            type(value) is type(allowed) and value == allowed
            for allowed in get_args(member)
        )
    if isinstance(member, type) and issubclass(member, (enum.Enum, Path)):
        return isinstance(value, member)
    if isinstance(member, type):
        return type(value) is member
    return get_origin(member) is None
