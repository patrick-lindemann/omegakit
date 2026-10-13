import dataclasses
import functools
import inspect
import itertools
import keyword
import re
import types
from collections.abc import Callable
from typing import (
    Any,
    NotRequired,
    Required,
    TypeAliasType,
    Union,
    get_args,
    get_origin,
    get_type_hints,
    is_typeddict,
)

from omegaconf import MISSING, OmegaConf
from omegaconf.errors import (
    OmegaConfBaseException,
)

from .configurable import Configurable
from .errors import (
    ConfigSchemaError,
    SchemaDefinitionError,
)
from .utils.describe import describe_error


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
    if not is_typeddict(schema):
        raise SchemaDefinitionError(
            f"`{target.__qualname__}.schema` must be a `TypedDict`, not `{schema!r}`."
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
        if is_typeddict(member):
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


def find_key_annotation(annotation: Any) -> Any:
    members = [
        member for member in split_union(annotation) if member is not types.NoneType
    ]
    if len(members) != 1 or get_origin(members[0]) is not dict:
        return Any
    return get_args(members[0])[0]


def find_tuple_annotations(annotation: Any, length: int) -> list[Any] | None:
    members = [
        member for member in split_union(annotation) if member is not types.NoneType
    ]
    if len(members) != 1 or (get_origin(members[0]) or members[0]) is not tuple:
        return None
    item_annotations = get_args(members[0])
    if not item_annotations:
        return [Any] * length
    if item_annotations[-1] is Ellipsis:
        return [item_annotations[0]] * length
    return list(item_annotations)


@functools.cache
def read_fields(schema: type) -> dict[str, SchemaField]:
    try:
        annotations = get_type_hints(schema)
        if is_typeddict(schema):
            required_keys = _read_required_keys(schema)
        else:
            required_keys = {
                field.name: (
                    field.default is dataclasses.MISSING
                    and field.default_factory is dataclasses.MISSING
                )
                # `MISSING` as the default marks a required field, as in OmegaConf
                or (isinstance(field.default, str) and field.default == MISSING)
                for field in dataclasses.fields(schema)
                if field.init
            }
    # Evaluating an annotation runs arbitrary code, which can raise anything
    except Exception as error:
        raise SchemaDefinitionError(
            f"Cannot read the annotations of `{schema.__qualname__}`: "
            f"{describe_error(error)}"
        ) from error
    fields = {}
    for name, is_required in required_keys.items():
        annotation = annotations[name]
        sections = [
            member for member in split_union(annotation) if is_typeddict(member)
        ]
        is_plain = is_data(annotation)
        if (
            not name.isidentifier()
            or keyword.iskeyword(name)
            or len(sections) > 1
            or (not is_plain and not _is_object(annotation))
        ):
            raise SchemaDefinitionError(
                f"`{schema.__qualname__}.{name}` is annotated with `{annotation}`. A "
                "key is a Python identifier, and its annotation is what OmegaConf "
                "supports, one `TypedDict` or a class."
            )
        fields[name] = SchemaField(annotation, is_plain, is_required)
    return fields


@functools.cache
def read_positions(schema: type) -> list[str]:
    parameters = inspect.signature(schema).parameters.values()
    kinds = (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    return [parameter.name for parameter in parameters if parameter.kind in kinds]


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
        raise ConfigSchemaError(
            f"{key} does not match `{schema.__qualname__}`: {describe_error(error)}"
        ) from error
    return {key: converted_values[key] for key in values}


def convert_item(annotation: Any, value: Any) -> Any:
    try:
        structure = _make_item_structure(annotation)
    # An annotation that cannot be hashed, such as `Literal[[1, 2]]`
    except TypeError:
        structure = _make_item_structure.__wrapped__(annotation)
    try:
        typed_item = OmegaConf.structured(structure(item=_escape_texts(value)))
        converted_item: Any = OmegaConf.to_container(typed_item, resolve=True)
    except (OmegaConfBaseException, OverflowError) as error:
        raise ConfigSchemaError(
            f"The item does not match `{annotation}`: {describe_error(error)}"
        ) from error
    return converted_item["item"]


def is_data(annotation: Any) -> bool:
    try:
        return _is_data_cached(annotation)
    # An annotation that cannot be hashed, such as `Literal[[1, 2]]`, is probed anew
    except TypeError:
        return _is_data_cached.__wrapped__(annotation)


@functools.cache
def _is_data_cached(annotation: Any) -> bool:
    # A dataclass is an object, although OmegaConf reads it as a structured config
    is_object = any(
        is_typeddict(member) or dataclasses.is_dataclass(member)
        for member in split_union(annotation)
    )
    if annotation is Any or is_object:
        return False
    item_annotation = find_item_annotation(annotation)
    if item_annotation is not None and not is_data(item_annotation):
        return False
    tuple_annotations = find_tuple_annotations(annotation, 1)
    if tuple_annotations is not None and not all(
        is_data(item) for item in tuple_annotations
    ):
        return False
    probe = dataclasses.make_dataclass("Probe", [("value", annotation)])
    try:
        OmegaConf.structured(probe)
    except OmegaConfBaseException:
        return False
    return True


def _read_required_keys(schema: type) -> dict[str, bool]:
    required_keys: dict[str, bool] = {}
    for base in types.get_original_bases(schema):
        if is_typeddict(base):
            required_keys |= _read_required_keys(base)
    # `__required_keys__` is wrong where the annotations are written as text
    annotations = get_type_hints(schema, include_extras=True)
    for name, annotation in annotations.items():
        if name not in required_keys:
            origin = get_origin(annotation)
            required_keys[name] = origin is Required or (
                origin is not NotRequired and schema.__total__
            )
    return required_keys


def _is_object(annotation: Any) -> bool:
    for member in split_union(annotation):
        item_annotation = find_item_annotation(member)
        if item_annotation is not None:
            if not _is_object(item_annotation):
                return False
            continue
        tuple_annotations = find_tuple_annotations(member, 1)
        if tuple_annotations is not None:
            if not all(_is_object(item) for item in tuple_annotations):
                return False
            continue
        cls = get_origin(member) or member
        if (
            not isinstance(cls, type)
            or cls in (set, frozenset)
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
def _make_item_structure(annotation: Any) -> type:
    return dataclasses.make_dataclass("Item", [("item", annotation)])


@functools.cache
def _make_structure(schema: type) -> type:
    # Every field has a default, so that the given values alone make an instance
    data_fields = [
        (name, field.annotation, dataclasses.field(default=MISSING))
        for name, field in read_fields(schema).items()
        if field.is_data
    ]
    return dataclasses.make_dataclass(schema.__name__, data_fields)
