import dataclasses
import functools
import itertools
import re
import types
from collections.abc import Callable
from typing import (
    Any,
    TypeAliasType,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)

from omegaconf import MISSING, OmegaConf
from omegaconf.errors import (
    ConfigKeyError,
    MissingMandatoryValue,
    OmegaConfBaseException,
    ValidationError,
)

from ._core.error import OmegaKitBaseException
from ._utils.describe import describe_error
from .configurable import Configurable


class ConfigSchemaError(OmegaKitBaseException):
    pass


class SchemaDefinitionError(ConfigSchemaError, TypeError):
    pass


class SchemaKeyError(ConfigSchemaError, ConfigKeyError):
    pass


class SchemaMissingValueError(ConfigSchemaError, MissingMandatoryValue):
    pass


class SchemaValueError(ConfigSchemaError, ValidationError):
    pass


class SchemaTypeError(ConfigSchemaError, ValidationError):
    pass


@dataclasses.dataclass(frozen=True)
class SchemaField:
    annotation: Any
    is_data: bool
    is_required: bool


def find_schema(target: Any) -> type | None:
    if not isinstance(target, type):
        return None
    schema = target.schema if issubclass(target, Configurable) else None
    if schema is None:
        return target if dataclasses.is_dataclass(target) else None
    if not (isinstance(schema, type) and dataclasses.is_dataclass(schema)):
        raise SchemaDefinitionError(
            f"`{target.__qualname__}.schema` must be a dataclass, not `{schema!r}`."
        )
    return schema


def split_union(annotation: Any) -> tuple[Any, ...]:
    while isinstance(annotation, TypeAliasType):
        annotation = annotation.__value__
    if get_origin(annotation) not in (Union, types.UnionType):
        return (annotation,)
    members = [split_union(member) for member in get_args(annotation)]
    return tuple(itertools.chain.from_iterable(members))


def find_section(annotation: Any) -> type | None:
    for member in split_union(annotation):
        if isinstance(member, type) and dataclasses.is_dataclass(member):
            return member
    return None


def find_item_annotation(
    annotation: Any, containers: tuple[type, ...] = (list, dict)
) -> Any:
    members = [
        member for member in split_union(annotation) if member is not types.NoneType
    ]
    if len(members) != 1 or (get_origin(members[0]) or members[0]) not in containers:
        return None
    item_annotations = get_args(members[0])
    return item_annotations[-1] if item_annotations else Any


@functools.cache
def read_fields(schema: type) -> dict[str, SchemaField]:
    try:
        annotations = get_type_hints(schema)
    # Evaluating an annotation runs arbitrary code, which can raise anything
    except Exception as error:
        raise SchemaDefinitionError(
            f"Cannot read the annotations of `{schema.__qualname__}`: "
            f"{describe_error(error)}"
        ) from error
    fields = {}
    for field in dataclasses.fields(schema):
        if not field.init:
            continue
        annotation = annotations[field.name]
        is_data = _is_data(annotation)
        if not is_data and not _is_object(annotation):
            raise SchemaDefinitionError(
                f"`{schema.__qualname__}.{field.name}` is annotated with "
                f"`{annotation}`, which OmegaConf does not support and which is not "
                "a class either."
            )
        has_default = (
            field.default is not dataclasses.MISSING
            or field.default_factory is not dataclasses.MISSING
        )
        # `MISSING` as the default marks a required field, as in OmegaConf
        is_required = not has_default or (
            isinstance(field.default, str) and field.default == MISSING
        )
        fields[field.name] = SchemaField(annotation, is_data, is_required)
    return fields


def convert_data(schema: type, values: dict[str, Any]) -> dict[str, Any]:
    structure = _make_structure(schema)
    escaped_values = {key: _escape_texts(value) for key, value in values.items()}
    try:
        typed_values = OmegaConf.structured(structure(**escaped_values))
        # Resolving decodes the escaped texts again
        converted_values: Any = OmegaConf.to_container(typed_values, resolve=True)
    # A number that is too large for a `float` raises an `OverflowError`
    except (OmegaConfBaseException, OverflowError) as error:
        full_key = getattr(error, "full_key", None)
        key = f"`{full_key}`" if full_key else "A value"
        raise SchemaValueError(
            f"{key} does not match `{schema.__qualname__}`: {describe_error(error)}"
        ) from error
    return {key: converted_values[key] for key in values}


def _is_data(annotation: Any) -> bool:
    try:
        return _is_data_cached(annotation)
    # An annotation that cannot be hashed, such as `Literal[[1, 2]]`, is probed anew
    except TypeError:
        return _is_data_cached.__wrapped__(annotation)


@functools.cache
def _is_data_cached(annotation: Any) -> bool:
    if annotation is Any or find_section(annotation) is not None:
        return False
    item_annotation = find_item_annotation(annotation)
    if item_annotation is not None and not _is_data(item_annotation):
        return False
    probe = dataclasses.make_dataclass("Probe", [("value", annotation)])
    try:
        OmegaConf.structured(probe)
    except OmegaConfBaseException:
        return False
    return True


def _is_object(annotation: Any) -> bool:
    for member in split_union(annotation):
        item_annotation = find_item_annotation(member)
        if item_annotation is not None:
            if not _is_object(item_annotation):
                return False
            continue
        cls = get_origin(member) or member
        if (
            not isinstance(cls, type)
            or cls in (tuple, set, frozenset)
            or (cls.__module__ == "collections.abc" and cls is not Callable)
        ):
            return False
    return True


def _escape_texts(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _escape_texts(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return type(value)(_escape_texts(item) for item in value)
    if not isinstance(value, str):
        return value
    # OmegaConf would read a resolved text as an interpolation or as `???` again
    escaped_value = re.sub(r"(\\*)\$\{", r"\1\1\\${", value)
    if re.fullmatch(r"\\*\?\?\?", escaped_value):
        return f"\\{escaped_value}"
    return escaped_value


@functools.cache
def _make_structure(schema: type) -> type:
    # Every field has a default, so that the given values alone make an instance
    data_fields = [
        (name, field.annotation, dataclasses.field(default=MISSING))
        for name, field in read_fields(schema).items()
        if field.is_data
    ]
    return dataclasses.make_dataclass(schema.__name__, data_fields)
