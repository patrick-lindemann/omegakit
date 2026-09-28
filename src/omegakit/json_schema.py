import collections.abc
import dataclasses
import enum
import types
from pathlib import Path
from typing import (
    Any,
    Literal,
    TypeAliasType,
    Union,
    get_args,
    get_origin,
    is_typeddict,
)

from .schema import classify_fields, find_schema

# A value may always be written as an interpolation, a missing value or an import.
_PLACEHOLDER = {"type": "string", "pattern": r"^(\?\?\?$|~import\s|.*\$\{)"}


def generate_json_schema(schema: type) -> dict[str, Any]:
    """Generate a JSON Schema for YAML config files.

    Args:
        schema: A root schema dataclass, or a `Configurable` class whose schema
            describes a fragment file.

    Returns:
        The JSON Schema (draft-07) as a dictionary.

    Raises:
        TypeError: If `schema` is neither a dataclass nor a `Configurable` with a
            dataclass schema.
        SchemaDefinitionError: If a schema that it reaches is not supported.
    """  # noqa: DOC503
    root = (find_schema(schema) or schema) if isinstance(schema, type) else None
    if not (isinstance(root, type) and dataclasses.is_dataclass(root)):
        name = getattr(schema, "__qualname__", repr(schema))
        raise TypeError(
            f"`{name}` is neither a dataclass nor a `Configurable` with a dataclass "
            "schema."
        )
    definitions: dict[str, Any] = {}
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        **_json_mapping(root, definitions),
        "definitions": definitions,
    }


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
    if origin in (Union, types.UnionType):
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
    if isinstance(annotation, type) and is_typeddict(annotation):
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
