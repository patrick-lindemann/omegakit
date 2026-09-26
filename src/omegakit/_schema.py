import collections.abc
import copy
import dataclasses
import enum
import functools
import inspect
import operator
import sys
import types
import typing
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal, TypeAliasType, get_args, get_origin, get_type_hints

from omegaconf import MISSING, OmegaConf
from omegaconf.errors import OmegaConfBaseException
from typing_extensions import NoDefault

from ._configurable import Configurable
from ._utils import format_path

type FieldKind = Literal["native", "object", "any"]

_NATIVE_TYPES = (int, float, bool, str, bytes, Path)
_UNSUPPORTED_CONTAINERS = (
    set,
    frozenset,
    tuple,
    collections.abc.Iterable,
    collections.abc.Collection,
    collections.abc.Sequence,
    collections.abc.MutableSequence,
    collections.abc.Set,
    collections.abc.MutableSet,
    collections.abc.Mapping,
    collections.abc.MutableMapping,
)
# A value may always be written as an interpolation, a missing value or an import.
_PLACEHOLDER = {"type": "string", "pattern": r"^(\?\?\?$|~import\s|.*\$\{)"}


class ConfigValidationError(ValueError):
    """A config does not match the schema of the class it builds."""

    __module__ = "omegakit"


@functools.cache
def find_schema(cls: type) -> type | None:
    """Find the dataclass schema of a `Configurable` class.

    The schema is the `TConfig` argument of `Configurable`, found by walking the
    original bases and substituting type variables. An unparametrized generic class
    uses the default of its type variable.

    Args:
        cls: The class to inspect.

    Returns:
        The schema dataclass, or `None` when `cls` is not a `Configurable` or its
        `TConfig` is not a dataclass.

    Raises:
        ConfigValidationError: If the schema uses a dataclass feature outside the
            supported subset.
    """
    if not issubclass(cls, Configurable):
        return None
    parameters = getattr(cls, "__parameters__", ())
    config_type = _find_config_type(
        cls, {parameter: _type_var_default(parameter) for parameter in parameters}
    )
    if not (isinstance(config_type, type) and dataclasses.is_dataclass(config_type)):
        return None
    try:
        OmegaConf.structured(_native_schema(config_type))
    except OmegaConfBaseException as error:
        raise ConfigValidationError(
            f"Schema `{config_type.__qualname__}` of `{cls.__qualname__}` cannot be "
            f"validated by OmegaConf: {str(error).splitlines()[0]}"
        ) from error
    return config_type


@functools.cache
def classify_fields(schema: type) -> dict[str, tuple[FieldKind, Any]]:
    """Classify the configurable fields of a schema dataclass.

    Fields with `init=False` and `InitVar` pseudo-fields are not configurable and
    are left out.

    Args:
        schema: The schema dataclass.

    Returns:
        The kind and resolved annotation of every configurable field, by field name.

    Raises:
        ConfigValidationError: If the schema uses a dataclass feature outside the
            supported subset.
    """
    hints = _type_hints(schema)
    for name, hint in hints.items():
        if isinstance(hint, dataclasses.InitVar) and not hasattr(schema, name):
            raise ConfigValidationError(
                f"Field `{name}` of schema `{schema.__qualname__}` is an `InitVar` "
                "without a default, which a config cannot set. Give it a default."
            )
    return {
        field.name: (
            _field_kind(hints[field.name], schema, field.name),
            hints[field.name],
        )
        for field in dataclasses.fields(schema)
        if field.init
    }


@functools.cache
def check_schema(cls: type) -> None:
    """Check that the schema of `cls` matches its `__init__`.

    The check applies only to the default `from_config`, which passes every schema
    field to the constructor. Classes without a schema, and classes whose MRO
    overrides `from_config`, pass unchecked. A successful check is cached.

    Args:
        cls: The class to check.

    Raises:
        ConfigValidationError: If a required parameter has no field, a field has no
            parameter and `__init__` takes no `**kwargs`, or a field's annotation is
            not assignable to its parameter's annotation.
    """
    schema = find_schema(cls)
    if schema is None or any(
        "from_config" in vars(base) for base in cls.__mro__ if base is not Configurable
    ):
        return
    fields = classify_fields(schema)
    parameters = inspect.signature(cls).parameters
    try:
        hints = get_type_hints(cls.__init__)
    except Exception:
        hints = {}
    keyword_names = {
        name
        for name, parameter in parameters.items()
        if parameter.kind
        in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
    }
    takes_kwargs = any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD
        for parameter in parameters.values()
    )
    for name, parameter in parameters.items():
        if (
            parameter.default is inspect.Parameter.empty
            and parameter.kind
            not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
            and name not in fields
        ):
            raise ConfigValidationError(
                f"Schema `{schema.__qualname__}` of `{cls.__qualname__}` has no field "
                f"for the required parameter `{name}`."
            )
    for name, (_, annotation) in fields.items():
        if name not in keyword_names:
            if takes_kwargs:
                continue
            raise ConfigValidationError(
                f"Field `{name}` of schema `{schema.__qualname__}` is not a keyword "
                f"parameter of `{cls.__qualname__}`, and `__init__` takes no "
                "`**kwargs`."
            )
        if name in hints and not _is_assignable(annotation, hints[name]):
            raise ConfigValidationError(
                f"Field `{name}` of schema `{schema.__qualname__}` has `{annotation}`, "
                f"which is not assignable to `{hints[name]}` in "
                f"`{cls.__qualname__}.__init__`."
            )


def validate_native(
    schema: type,
    values: dict[str, Any],
    path: tuple[str | int, ...],
    allow_missing: bool = False,
) -> dict[str, Any]:
    """Validate and coerce the native fields of a node through OmegaConf.

    Args:
        schema: The schema dataclass.
        values: The node's resolved values, without `$` keys.
        path: The node's path from the config root.
        allow_missing: Keep missing values as `???` instead of raising, including
            required fields that are not given. Defaults to `False`.

    Returns:
        The coerced native fields, including defaults for absent ones.

    Raises:
        ConfigValidationError: If a key is not a field, a required field is missing,
            or a native value does not match its annotation.
    """
    fields = classify_fields(schema)
    location = f"`{format_path(path)}` ({schema.__qualname__})"
    unknown = [key for key in values if key not in fields]
    if unknown:
        raise ConfigValidationError(
            f"Unknown field(s) {', '.join(map(repr, unknown))} in {location}. "
            f"Expected one of: {', '.join(fields)}."
        )
    for field in dataclasses.fields(schema):
        if (
            not allow_missing
            and field.name in fields
            and field.name not in values
            and fields[field.name][0] != "native"
            and field.default is dataclasses.MISSING
            and field.default_factory is dataclasses.MISSING
        ):
            raise ConfigValidationError(
                f"Missing required field `{field.name}` in {location}."
            )
    native = {
        key: _normalize_enums(value, fields[key][1])
        for key, value in values.items()
        if fields[key][0] == "native"
    }
    try:
        merged = OmegaConf.to_container(
            OmegaConf.merge(OmegaConf.structured(_native_schema(schema)), native),
            resolve=True,
            throw_on_missing=not allow_missing,
        )
    except OmegaConfBaseException as error:
        message = str(error).splitlines()[0]
        if error.full_key:
            location = (
                f"`{format_path((*path, error.full_key))}` ({schema.__qualname__})"
            )
        raise ConfigValidationError(
            f"Invalid config in {location}: {message}"
        ) from error
    merged = typing.cast(dict[str, Any], merged)
    return {
        name: _build_native_value(
            merged[name], annotation, (*path, name), allow_missing
        )
        for name, (kind, annotation) in fields.items()
        if kind == "native"
    }


def find_section(annotation: Any) -> type | None:
    """Find the dataclass in an object field's annotation, if there is one.

    A plain mapping in such a field is a section of the schema, not a node to build.

    Args:
        annotation: The field's annotation, possibly a union or a `type` alias.

    Returns:
        The first dataclass among the annotation's members, or `None`.
    """
    while isinstance(annotation, TypeAliasType):
        annotation = annotation.__value__
    if get_origin(annotation) in (typing.Union, types.UnionType):
        members = get_args(annotation)
    else:
        members = (annotation,)
    for member in members:
        if isinstance(member, type) and dataclasses.is_dataclass(member):
            return member
    return None


def generate_json_schema(schema: type) -> dict[str, Any]:
    """Generate a JSON Schema for YAML config files.

    Every value may also be an interpolation (`${...}`), `???` or an `~import`, every
    mapping accepts `$`-keys such as `$base` and `$class`, and nothing is required,
    because values may come from `$base`, `$defaults` or overrides. Enums are given by
    member name. An object field whose class is a `Configurable` with a dataclass
    schema is checked against that schema when its `$class` names the class.

    Args:
        schema: A root schema dataclass, or a `Configurable` class whose schema
            describes a fragment file.

    Returns:
        The JSON Schema (draft-07) as a dictionary.

    Raises:
        TypeError: If `schema` is neither a dataclass nor a `Configurable` with a
            dataclass schema.
    """
    root = find_schema(schema) or schema
    if not dataclasses.is_dataclass(root):
        raise TypeError(
            f"`{schema.__qualname__}` is neither a dataclass nor a `Configurable` with "
            "a dataclass schema."
        )
    definitions: dict[str, Any] = {}
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        **_json_mapping(root, definitions),
        "definitions": definitions,
    }


def _type_var_default(parameter: Any) -> Any:
    return getattr(parameter, "__default__", NoDefault)


def _find_config_type(cls: type, substitutions: dict[Any, Any]) -> Any:
    for base in types.get_original_bases(cls):
        origin = get_origin(base) or base
        if not (isinstance(origin, type) and issubclass(origin, Configurable)):
            continue
        arguments = tuple(
            _substitute(argument, substitutions, cls) for argument in get_args(base)
        )
        parameters = getattr(origin, "__parameters__", ())
        if not arguments:
            arguments = tuple(_type_var_default(parameter) for parameter in parameters)
        if origin is Configurable:
            return arguments[0]
        return _find_config_type(origin, dict(zip(parameters, arguments, strict=True)))
    return NoDefault


def _substitute(argument: Any, substitutions: dict[Any, Any], cls: type) -> Any:
    if not isinstance(argument, typing.TypeVar):
        return argument
    if argument not in substitutions:
        raise TypeError(
            f"Cannot resolve type variable `{argument}` in the bases of "
            f"`{cls.__qualname__}`."
        )
    return substitutions[argument]


def _type_hints(schema: type) -> dict[str, Any]:
    try:
        return get_type_hints(schema)
    except NameError as error:
        namespace = vars(sys.modules[schema.__module__])
        for field in dataclasses.fields(schema):
            if not isinstance(field.type, str):
                continue
            try:
                eval(field.type, namespace, dict(vars(schema)))
            except NameError:
                raise ConfigValidationError(
                    f"Cannot resolve the annotation of field `{field.name}` of schema "
                    f"`{schema.__qualname__}`: {error}. Import the type at module "
                    "level, not under `TYPE_CHECKING` or inside a function."
                ) from error
        raise ConfigValidationError(
            f"Cannot resolve the annotations of schema `{schema.__qualname__}`: "
            f"{error}."
        ) from error


def _field_kind(annotation: Any, schema: type, name: str) -> FieldKind:
    while isinstance(annotation, TypeAliasType):
        annotation = annotation.__value__
    origin = get_origin(annotation)
    arguments = get_args(annotation)
    if origin is Literal:
        if all(type(value) in (str, int, bool) for value in arguments):
            return "native"
        raise ConfigValidationError(
            f"Field `{name}` of schema `{schema.__qualname__}` has `{annotation}`, but "
            "`Literal` values must be strings, integers or booleans."
        )
    if annotation is Any:
        return "any"
    if annotation in _NATIVE_TYPES or (
        isinstance(annotation, type) and issubclass(annotation, enum.Enum)
    ):
        return "native"
    if isinstance(annotation, type) and dataclasses.is_dataclass(annotation):
        kinds = {kind for kind, _ in classify_fields(annotation).values()}
        return "native" if kinds <= {"native"} else "object"
    if isinstance(annotation, type) and typing.is_typeddict(annotation):
        return "native"
    if origin in (typing.Union, types.UnionType):
        members = [member for member in arguments if member is not type(None)]
        member_kinds: set[FieldKind] = {
            _field_kind(member, schema, name) for member in members
        }
        if len(member_kinds) > 1:
            raise ConfigValidationError(
                f"Field `{name}` of schema `{schema.__qualname__}` mixes value types "
                f"and classes in `{annotation}`. Use a union of plain values, a union "
                "of classes, or `Any`."
            )
        kind = member_kinds.pop()
        if kind == "native" and (
            sum(_is_mapping_type(member) for member in members) > 1
            or sum(_is_sequence_type(member) for member in members) > 1
        ):
            raise ConfigValidationError(
                f"Field `{name}` of schema `{schema.__qualname__}` has `{annotation}`, "
                "whose mapping or list members cannot be told apart. Use at most one "
                "mapping type and one list type in a union, or `Any`."
            )
        return kind
    if annotation in (list, dict, tuple) or origin in (
        list,
        dict,
        tuple,
        collections.abc.Sequence,
        collections.abc.Mapping,
    ):
        items = [argument for argument in arguments if argument is not Ellipsis]
        if origin is dict or origin is collections.abc.Mapping:
            items = items[1:]
        kinds: set[FieldKind] = {_field_kind(item, schema, name) for item in items}
        if kinds <= {"native"}:
            return "native"
        if kinds == {"object"} and origin in (list, dict):
            return "object"
        if kinds == {"any"}:
            return "any"
        raise ConfigValidationError(
            f"Field `{name}` of schema `{schema.__qualname__}` has `{annotation}`, "
            "but a container can hold either plain values or objects, and objects "
            "only in `list` and `dict`. Use `Any` otherwise."
        )
    if annotation in _UNSUPPORTED_CONTAINERS or origin in _UNSUPPORTED_CONTAINERS:
        raise ConfigValidationError(
            f"Field `{name}` of schema `{schema.__qualname__}` has the unsupported "
            f"container `{annotation}`. Use `list`, `dict`, `tuple` or `Any`."
        )
    if origin is None and isinstance(annotation, type):
        return "object"
    if isinstance(origin, type):
        return "object"
    raise ConfigValidationError(
        f"Field `{name}` of schema `{schema.__qualname__}` has the unsupported "
        f"annotation `{annotation}`."
    )


def _is_mapping_type(annotation: Any) -> bool:
    origin = get_origin(annotation) or annotation
    return origin in (dict, collections.abc.Mapping) or (
        isinstance(annotation, type)
        and (dataclasses.is_dataclass(annotation) or typing.is_typeddict(annotation))
    )


def _is_sequence_type(annotation: Any) -> bool:
    origin = get_origin(annotation) or annotation
    return origin in (list, tuple, collections.abc.Sequence)


# OmegaConf 2.3 supports neither `Literal`, nor unions with non-scalar members, nor
# fixed-length tuples, so it validates against a derived structure that holds plain
# types there. `_build_native_value` checks the rest and builds the schema's own
# classes, so every supported OmegaConf version behaves the same.
@functools.cache
def _native_schema(schema: type) -> type:
    structure = []
    for field in dataclasses.fields(schema):
        if field.name not in classify_fields(schema):
            continue
        kind, annotation = classify_fields(schema)[field.name]
        if kind != "native":
            continue
        structure_type = _structure_type(annotation)
        if field.default_factory is not dataclasses.MISSING:
            default = dataclasses.field(
                default_factory=functools.partial(
                    _structure_default, field.default_factory, structure_type is Any
                )
            )
        elif field.default is not dataclasses.MISSING:
            default = dataclasses.field(
                default_factory=functools.partial(
                    _structure_default,
                    functools.partial(copy.deepcopy, field.default),
                    structure_type is Any,
                )
            )
        else:
            default = dataclasses.field(default=MISSING)
        structure.append((field.name, structure_type, default))
    return dataclasses.make_dataclass(schema.__name__, structure, kw_only=True)


def _structure_type(annotation: Any) -> Any:
    while isinstance(annotation, TypeAliasType):
        annotation = annotation.__value__
    origin = get_origin(annotation)
    arguments = get_args(annotation)
    if origin is Literal:
        return functools.reduce(
            operator.or_, dict.fromkeys(type(value) for value in arguments)
        )
    if origin in (typing.Union, types.UnionType):
        members = [member for member in arguments if member is not type(None)]
        if len(members) == 1:
            return _structure_type(members[0]) | None
        if any(
            _is_mapping_type(member) or _is_sequence_type(member)
            for member in arguments
        ):
            return Any
        return functools.reduce(operator.or_, map(_structure_type, arguments))
    if origin in (list, collections.abc.Sequence) or (
        origin is tuple and len(arguments) == 2 and arguments[1] is Ellipsis
    ):
        return list[_structure_type(arguments[0])]
    if origin is tuple:
        return Any
    if origin in (dict, collections.abc.Mapping):
        return dict[arguments[0], _structure_type(arguments[1])]
    if isinstance(annotation, type) and typing.is_typeddict(annotation):
        return dict
    if isinstance(annotation, type) and dataclasses.is_dataclass(annotation):
        return _native_schema(annotation)
    return annotation


def _structure_default(factory: Callable[[], Any], plain: bool) -> Any:
    return _to_structure(factory(), plain)


def _to_structure(value: Any, plain: bool) -> Any:
    # A field that is `Any` in the structure takes plain containers: a dataclass
    # default there would stay typed and reject other union members.
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        items = {
            name: _to_structure(getattr(value, name), plain)
            for name in classify_fields(type(value))
        }
        return items if plain else _native_schema(type(value))(**items)
    if isinstance(value, (list, tuple)):
        return [_to_structure(item, plain) for item in value]
    if isinstance(value, dict):
        return {key: _to_structure(item, plain) for key, item in value.items()}
    return value


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
    if origin in (typing.Union, types.UnionType):
        members = [member for member in arguments if member is not type(None)]
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
    value: Any, annotation: Any, path: tuple[str | int, ...], allow_missing: bool
) -> Any:
    # Validates one value against an annotation through OmegaConf, as a field would.
    try:
        merged = OmegaConf.to_container(
            OmegaConf.merge(
                OmegaConf.structured(_value_structure(annotation)),
                {"value": _normalize_enums(value, annotation)},
            ),
            resolve=True,
            throw_on_missing=not allow_missing,
        )
    except OmegaConfBaseException as error:
        raise ConfigValidationError(
            f"Invalid config in `{format_path(path)}`: {str(error).splitlines()[0]}"
        ) from error
    return _build_native_value(
        typing.cast(dict[str, Any], merged)["value"], annotation, path, allow_missing
    )


@functools.cache
def _value_structure(annotation: Any) -> type:
    return dataclasses.make_dataclass(
        "Value", [("value", _structure_type(annotation), dataclasses.field())]
    )


def _build_native_value(
    value: Any, annotation: Any, path: tuple[str | int, ...], allow_missing: bool
) -> Any:
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
                f"{', '.join(map(repr, arguments))}, but the config gives {value!r}."
            )
        return value
    if origin in (typing.Union, types.UnionType):
        return _build_union_value(value, annotation, path, allow_missing)
    if origin in (list, collections.abc.Sequence):
        return [
            _build_native_value(item, arguments[0], (*path, index), allow_missing)
            for index, item in enumerate(value)
        ]
    if origin is tuple and len(arguments) == 2 and arguments[1] is Ellipsis:
        return tuple(
            _build_native_value(item, arguments[0], (*path, index), allow_missing)
            for index, item in enumerate(value)
        )
    if origin is tuple:
        if not isinstance(value, (list, tuple)) or len(value) != len(arguments):
            raise ConfigValidationError(
                f"`{format_path(path)}` expects a list of {len(arguments)} items for "
                f"`{annotation}`, but the config gives {value!r}."
            )
        return tuple(
            _coerce(item, item_annotation, (*path, index), allow_missing)
            for index, (item, item_annotation) in enumerate(
                zip(value, arguments, strict=True)
            )
        )
    if origin in (dict, collections.abc.Mapping):
        return {
            key: _build_native_value(item, arguments[1], (*path, key), allow_missing)
            for key, item in value.items()
        }
    if isinstance(annotation, type) and dataclasses.is_dataclass(annotation):
        fields = classify_fields(annotation)
        return annotation(
            **{
                name: _build_native_value(
                    item, fields[name][1], (*path, name), allow_missing
                )
                for name, item in value.items()
            }
        )
    return value


def _build_union_value(
    value: Any, annotation: Any, path: tuple[str | int, ...], allow_missing: bool
) -> Any:
    members = [member for member in get_args(annotation) if member is not type(None)]
    if value is None and len(members) < len(get_args(annotation)):
        return None
    if len(members) == 1:
        return _build_native_value(value, members[0], path, allow_missing)
    if isinstance(value, dict):
        for member in members:
            if _is_mapping_type(member):
                return _coerce(value, member, path, allow_missing)
    elif isinstance(value, (list, tuple)):
        for member in members:
            if _is_sequence_type(member):
                return _coerce(value, member, path, allow_missing)
    elif any(_is_match(value, member) for member in members):
        return value
    raise ConfigValidationError(
        f"`{format_path(path)}` expects `{annotation}`, but the config gives {value!r}."
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


def _is_assignable(source: Any, target: Any) -> bool:
    while isinstance(source, TypeAliasType):
        source = source.__value__
    while isinstance(target, TypeAliasType):
        target = target.__value__
    if source is Any or target is Any:
        return True
    if get_origin(source) in (typing.Union, types.UnionType):
        return all(_is_assignable(member, target) for member in get_args(source))
    if get_origin(target) in (typing.Union, types.UnionType):
        return any(_is_assignable(source, member) for member in get_args(target))
    if get_origin(source) is not None or get_origin(target) is not None:
        return True
    if not (isinstance(source, type) and isinstance(target, type)):
        return True
    if target is float and source is int:
        return True
    if target is complex and source in (int, float):
        return True
    return issubclass(source, target)


def _json_value(annotation: Any, definitions: dict[str, Any]) -> dict[str, Any]:
    return {"anyOf": [_json_type(annotation, definitions), _PLACEHOLDER]}


def _json_type(annotation: Any, definitions: dict[str, Any]) -> dict[str, Any]:
    while isinstance(annotation, TypeAliasType):
        annotation = annotation.__value__
    origin = get_origin(annotation)
    arguments = get_args(annotation)
    if annotation is Any:
        return {}
    if annotation is type(None):
        return {"type": "null"}
    if origin in (typing.Union, types.UnionType):
        return {"anyOf": [_json_type(argument, definitions) for argument in arguments]}
    if annotation is bool:
        return {"type": "boolean"}
    if annotation is int:
        return {"type": "integer"}
    if annotation is float:
        return {"type": "number"}
    if annotation in (str, bytes, Path):
        return {"type": "string"}
    if isinstance(annotation, type) and issubclass(annotation, enum.Enum):
        names = [member.name for member in annotation]
        values = [
            member.value
            for member in annotation
            if type(member.value) in (str, int) and member.value not in names
        ]
        return {"enum": list(dict.fromkeys([*names, *values]))}
    if origin is Literal:
        return {"enum": list(arguments)}
    if origin is tuple and not (len(arguments) == 2 and arguments[1] is Ellipsis):
        return {
            "type": "array",
            "items": [_json_value(argument, definitions) for argument in arguments],
            "minItems": len(arguments),
            "maxItems": len(arguments),
        }
    if annotation in (list, tuple) or origin in (
        list,
        tuple,
        collections.abc.Sequence,
    ):
        items = _json_value(arguments[0], definitions) if arguments else {}
        return {"type": "array", "items": items}
    if annotation is dict or origin in (dict, collections.abc.Mapping):
        values = _json_value(arguments[1], definitions) if arguments else {}
        return {"type": "object", "additionalProperties": values}
    if isinstance(annotation, type) and typing.is_typeddict(annotation):
        return {"type": "object"}
    if isinstance(annotation, type) and dataclasses.is_dataclass(annotation):
        return {"$ref": f"#/definitions/{_json_definition(annotation, definitions)}"}
    if isinstance(annotation, type):
        return _json_object(annotation, definitions)
    if isinstance(origin, type):
        return _json_object(origin, definitions)
    return {}


def _json_object(cls: Any, definitions: dict[str, Any]) -> dict[str, Any]:
    schema = find_schema(cls) if isinstance(cls, type) else None
    if schema is None:
        return {"type": "object"}
    return {
        "type": "object",
        "if": {
            "properties": {"$class": {"const": f"{cls.__module__}.{cls.__qualname__}"}},
            "required": ["$class"],
        },
        "then": {"$ref": f"#/definitions/{_json_definition(schema, definitions)}"},
    }


def _json_definition(dataclass: type, definitions: dict[str, Any]) -> str:
    name = f"{dataclass.__module__}.{dataclass.__qualname__}"
    if name not in definitions:
        definitions[name] = {}
        definitions[name] = _json_mapping(dataclass, definitions)
    return name


def _json_mapping(dataclass: type, definitions: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            name: _json_value(annotation, definitions)
            for name, (_, annotation) in classify_fields(dataclass).items()
        },
        "patternProperties": {r"^\$": {}},
        "additionalProperties": False,
    }
