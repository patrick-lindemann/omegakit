import collections.abc
import dataclasses
import functools
import types
from collections.abc import Iterator, Mapping
from typing import (
    Any,
    ClassVar,
    Literal,
    Protocol,
    TypeAliasType,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)

from omegaconf import OmegaConf, SCMode
from omegaconf.errors import OmegaConfBaseException

from .errors import ConfigValidationError, OmegaKitBaseException, SchemaDefinitionError
from .utils import describe_error, format_full_key, format_path


# Dataclasses share no base class. This is typeshed's `DataclassInstance`, which
# exists only for type checkers.
class _DataclassInstance(Protocol):
    __dataclass_fields__: ClassVar[dict[str, dataclasses.Field[Any]]]


type Schema = type[_DataclassInstance]
"""A class that declares the fields of a config node: a dataclass."""

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


def coerce_fields(
    schema: Schema,
    values: dict[str, Any],
    path: tuple[str | int, ...],
    allow_missing: bool = False,
    build: bool = False,
) -> dict[str, Any]:
    """Check the fields of a node through OmegaConf, and convert its data fields.

    Args:
        schema: The schema of the node.
        values: The node's resolved values, without `$` keys. With `build`, the
            fields that are not data hold built objects.
        path: The node's path from the config root.
        allow_missing: Accept `???` and required fields that are not given.
            Defaults to `False`.
        build: Build the dataclasses in the data fields. Without it, they stay
            mappings. Defaults to `False`.

    Returns:
        The converted data fields. An absent field with a default is left out, so
        that the schema fills it in itself.

    Raises:
        ConfigValidationError: If OmegaConf rejects the node: a key that is not a
            field, a missing required field, or a wrong value.
        SchemaDefinitionError: If OmegaConf cannot check the schema.
    """  # noqa: DOC503
    fields = classify_fields(schema)
    try:
        structure = OmegaConf.structured(_derive_structure(schema))
    except OmegaKitBaseException:
        raise
    except OmegaConfBaseException as error:
        raise SchemaDefinitionError(
            f"Schema `{schema.__qualname__}` cannot be validated by OmegaConf: "
            f"{describe_error(error)}"
        ) from error
    # Objects are omegakit's to check and build; their fields hold `Any` in the
    # structure, which only tells whether they are given.
    given = {
        key: None if key in fields and fields[key][0] != "data" else value
        for key, value in values.items()
    }
    try:
        converted: Any = OmegaConf.to_container(
            OmegaConf.merge(structure, given),
            resolve=True,
            throw_on_missing=not allow_missing,
            structured_config_mode=SCMode.INSTANTIATE if build else SCMode.DICT,
        )
    except OmegaKitBaseException:
        raise
    except OmegaConfBaseException as error:
        location = (*path, format_full_key(error.full_key)) if error.full_key else path
        raise ConfigValidationError(
            f"Invalid config in `{format_path(location)}` ({schema.__qualname__}): "
            f"{describe_error(error)}"
        ) from error
    if build:
        converted = vars(converted)
    return {
        name: converted[name]
        for name, (kind, _) in fields.items()
        if kind == "data"
        and (name in values or name not in _find_defaulted_fields(schema))
    }


def split_union(annotation: Any) -> tuple[tuple[Any, ...], bool]:
    """Split an annotation into its members, following type aliases.

    Args:
        annotation: The annotation, possibly a union or a `type` alias.

    Returns:
        The members of a union other than `None`, or the annotation alone, and
        whether the union contains `None`.
    """
    while isinstance(annotation, TypeAliasType):
        annotation = annotation.__value__
    if get_origin(annotation) not in (Union, types.UnionType):
        return (annotation,), False
    members = tuple(
        member for member in get_args(annotation) if member is not type(None)
    )
    return members, len(members) < len(get_args(annotation))


def find_section(annotation: Any) -> Schema | None:
    """Find the dataclass in an object field's annotation, if there is one.

    Args:
        annotation: The field's annotation, possibly a union or a `type` alias.

    Returns:
        The first dataclass among the annotation's members, or `None`.
    """
    members, _ = split_union(annotation)
    for member in members:
        if isinstance(member, type) and dataclasses.is_dataclass(member):
            return member
    return None


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


@functools.cache
def _derive_structure(schema: Schema) -> type:
    fields = classify_fields(schema)
    structure = []
    for field in dataclasses.fields(schema):
        if field.name not in fields:
            continue
        kind, annotation = fields[field.name]
        if kind == "data":
            default = dataclasses.field(
                default=field.default, default_factory=field.default_factory
            )
        elif (
            field.default is dataclasses.MISSING
            and field.default_factory is dataclasses.MISSING
        ):
            default = dataclasses.field()
        else:
            default = dataclasses.field(default=None)
        structure.append((field.name, annotation if kind == "data" else Any, default))
    return dataclasses.make_dataclass(schema.__name__, structure, kw_only=True)


@functools.cache
def _find_defaulted_fields(schema: Schema) -> frozenset[str]:
    return frozenset(
        field.name
        for field in dataclasses.fields(schema)
        if field.default is not dataclasses.MISSING
        or field.default_factory is not dataclasses.MISSING
    )
