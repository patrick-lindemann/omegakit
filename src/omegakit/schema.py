import collections.abc
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

from omegaconf import OmegaConf
from omegaconf.errors import OmegaConfBaseException
from typing_extensions import NoDefault

from .configurable import Configurable
from .keys import PARTIAL_KEY
from .utils import format_path

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
    """Classify the fields of a schema dataclass.

    Args:
        schema: The schema dataclass.

    Returns:
        The kind and resolved annotation of every field, by field name.

    Raises:
        ConfigValidationError: If the schema uses a dataclass feature outside the
            supported subset.
    """
    hints = _type_hints(schema)
    for name, hint in hints.items():
        if isinstance(hint, dataclasses.InitVar):
            raise ConfigValidationError(
                f"Field `{name}` of schema `{schema.__qualname__}` is an `InitVar`, "
                "which schemas do not support. Make it a regular field."
            )
    fields = {}
    for field in dataclasses.fields(schema):
        if not field.init:
            raise ConfigValidationError(
                f"Field `{field.name}` of schema `{schema.__qualname__}` has "
                "`init=False`, which schemas do not support."
            )
        if field.kw_only:
            raise ConfigValidationError(
                f"Field `{field.name}` of schema `{schema.__qualname__}` is "
                "keyword-only, which schemas do not support."
            )
        hint = hints[field.name]
        fields[field.name] = (_field_kind(hint, schema, field.name), hint)
    return fields


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
    schema: type, values: dict[str, Any], path: tuple[str | int, ...]
) -> dict[str, Any]:
    """Validate and coerce the native fields of a node through OmegaConf.

    Args:
        schema: The schema dataclass.
        values: The node's resolved values, without `$` keys.
        path: The node's path from the config root.

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
            field.name not in values
            and fields[field.name][0] != "native"
            and field.default is dataclasses.MISSING
            and field.default_factory is dataclasses.MISSING
        ):
            raise ConfigValidationError(
                f"Missing required field `{field.name}` in {location}."
            )
    native = {key: value for key, value in values.items() if fields[key][0] == "native"}
    try:
        merged = OmegaConf.to_container(
            OmegaConf.merge(OmegaConf.structured(_native_schema(schema)), native),
            resolve=True,
            throw_on_missing=True,
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
        name: _build_native_value(merged[name], annotation, (*path, name))
        for name, (kind, annotation) in fields.items()
        if kind == "native"
    }


def check_object(
    value: Any, annotation: Any, raw: Any, path: tuple[str | int, ...], schema: type
) -> None:
    """Check that a built object field matches its annotation.

    The check is skipped for partials (`$partial: true`), for generic or other
    non-class annotations, and when `isinstance` raises `TypeError`, as it does for
    protocols that are not runtime-checkable.

    Args:
        value: The built value.
        annotation: The field's annotation.
        raw: The field's resolved config value before building.
        path: The field's path from the config root.
        schema: The schema dataclass the field belongs to.

    Raises:
        ConfigValidationError: If `value` is not an instance of the annotation.
    """
    if isinstance(raw, dict) and raw.get(PARTIAL_KEY) is True:
        return
    while isinstance(annotation, TypeAliasType):
        annotation = annotation.__value__
    if get_origin(annotation) in (typing.Union, types.UnionType):
        classes = tuple(
            member.__value__ if isinstance(member, TypeAliasType) else member
            for member in get_args(annotation)
        )
    else:
        classes = (annotation,)
    if not all(isinstance(member, type) for member in classes):
        return
    try:
        valid = isinstance(value, classes)
    except TypeError:
        return
    if not valid:
        expected = " | ".join(member.__qualname__ for member in classes)
        raise ConfigValidationError(
            f"Field `{format_path(path)}` of schema `{schema.__qualname__}` expects "
            f"{expected}, but the config gave {type(value).__qualname__}."
        )


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
    if origin is Literal:
        if all(type(value) in (str, int, bool) for value in get_args(annotation)):
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
        return "native" if kinds == {"native"} else "object"
    if origin in (typing.Union, types.UnionType):
        member_kinds: set[FieldKind] = {
            _field_kind(member, schema, name)
            for member in get_args(annotation)
            if member is not type(None)
        }
        if len(member_kinds) == 1:
            return member_kinds.pop()
        raise ConfigValidationError(
            f"Field `{name}` of schema `{schema.__qualname__}` mixes value types and "
            f"classes in `{annotation}`. Use a union of plain values, a union of "
            "classes, or `Any`."
        )
    if annotation in (list, dict) or (
        origin in (list, dict)
        and all(
            _field_kind(argument, schema, name) == "native"
            for argument in get_args(annotation)
        )
    ):
        return "native"
    if origin in (list, dict):
        raise ConfigValidationError(
            f"Field `{name}` of schema `{schema.__qualname__}` has `{annotation}`, "
            "but containers can only hold plain values and dataclasses. Use `Any` "
            "for containers of objects."
        )
    if annotation in _UNSUPPORTED_CONTAINERS or origin in _UNSUPPORTED_CONTAINERS:
        raise ConfigValidationError(
            f"Field `{name}` of schema `{schema.__qualname__}` has the unsupported "
            f"container `{annotation}`. Use `list`, `dict` or `Any`."
        )
    if origin is None and isinstance(annotation, type):
        if typing.is_typeddict(annotation):
            raise ConfigValidationError(
                f"Field `{name}` of schema `{schema.__qualname__}` is a `TypedDict`, "
                "which schemas do not support. Use a dataclass."
            )
        return "object"
    if isinstance(origin, type):
        return "object"
    raise ConfigValidationError(
        f"Field `{name}` of schema `{schema.__qualname__}` has the unsupported "
        f"annotation `{annotation}`."
    )


# OmegaConf does not support `Literal`, so it validates against a derived structure
# with plain value types. `_build_native_value` checks the literals and builds the
# schema's own classes from the result.
@functools.cache
def _native_schema(schema: type) -> type:
    fields = classify_fields(schema)
    structure = []
    for field in dataclasses.fields(schema):
        kind, annotation = fields[field.name]
        if kind != "native":
            continue
        if field.default_factory is dataclasses.MISSING:
            default = dataclasses.field(default=field.default)
        else:
            default = dataclasses.field(
                default_factory=functools.partial(
                    _structure_default, field.default_factory
                )
            )
        structure.append((field.name, _structure_type(annotation), default))
    return dataclasses.make_dataclass(schema.__name__, structure)


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
        return functools.reduce(operator.or_, map(_structure_type, arguments))
    if origin is list:
        return list[_structure_type(arguments[0])]
    if origin is dict:
        return dict[arguments[0], _structure_type(arguments[1])]
    if isinstance(annotation, type) and dataclasses.is_dataclass(annotation):
        return _native_schema(annotation)
    return annotation


def _structure_default(factory: Callable[[], Any]) -> Any:
    return _to_structure(factory())


def _to_structure(value: Any) -> Any:
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return _native_schema(type(value))(
            **{
                field.name: _to_structure(getattr(value, field.name))
                for field in dataclasses.fields(value)
            }
        )
    if isinstance(value, list):
        return [_to_structure(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_structure(item) for key, item in value.items()}
    return value


def _build_native_value(
    value: Any, annotation: Any, path: tuple[str | int, ...]
) -> Any:
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
        members = [member for member in arguments if member is not type(None)]
        if value is None:
            return None
        if len(members) == 1:
            return _build_native_value(value, members[0], path)
        if any(get_origin(member) is Literal for member in members) and not any(
            _is_match(value, member) for member in members
        ):
            raise ConfigValidationError(
                f"`{format_path(path)}` expects `{annotation}`, but the config gives "
                f"{value!r}."
            )
        return value
    if origin is list:
        return [
            _build_native_value(item, arguments[0], (*path, index))
            for index, item in enumerate(value)
        ]
    if origin is dict:
        return {
            key: _build_native_value(item, arguments[1], (*path, key))
            for key, item in value.items()
        }
    if isinstance(annotation, type) and dataclasses.is_dataclass(annotation):
        hints = _type_hints(annotation)
        return annotation(
            **{
                name: _build_native_value(item, hints[name], (*path, name))
                for name, item in value.items()
            }
        )
    return value


def _is_match(value: Any, member: Any) -> bool:
    while isinstance(member, TypeAliasType):
        member = member.__value__
    if get_origin(member) is Literal:
        return any(
            type(value) is type(allowed) and value == allowed
            for allowed in get_args(member)
        )
    if isinstance(member, type):
        return isinstance(value, member)
    return True


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
        return {"enum": [member.name for member in annotation]}
    if origin is Literal:
        return {"enum": list(arguments)}
    if annotation is list or origin is list:
        items = _json_value(arguments[0], definitions) if arguments else {}
        return {"type": "array", "items": items}
    if annotation is dict or origin is dict:
        values = _json_value(arguments[1], definitions) if arguments else {}
        return {"type": "object", "additionalProperties": values}
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
    hints = get_type_hints(dataclass)
    return {
        "type": "object",
        "properties": {
            field.name: _json_value(hints[field.name], definitions)
            for field in dataclasses.fields(dataclass)
        },
        "patternProperties": {r"^\$": {}},
        "additionalProperties": False,
    }
