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

from .assembly import IMPORT_KEY
from .object import CLASS_KEY
from .schema import classify_fields, find_schema

# A value may always be written as an interpolation, a missing value or an import.
_PLACEHOLDER = {
    "type": "string",
    "pattern": rf"^(\?\?\?$|{IMPORT_KEY}\s|.*\$\{{)",
}


def generate_json_schema(schema: type) -> dict[str, Any]:
    """Generate a JSON Schema for YAML config files.

    Args:
        schema: A dataclass that describes a whole config file, or a `Configurable`
            class whose schema describes a fragment file.

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
        **_build_mapping_schema(root, definitions),
        "definitions": definitions,
    }


def _build_value_schema(annotation: Any, definitions: dict[str, Any]) -> dict[str, Any]:
    return {"anyOf": [_build_type_schema(annotation, definitions), _PLACEHOLDER]}


def _build_type_schema(annotation: Any, definitions: dict[str, Any]) -> dict[str, Any]:
    while isinstance(annotation, TypeAliasType):
        annotation = annotation.__value__
    origin = get_origin(annotation)
    arguments = get_args(annotation)
    if annotation is Any:
        return {}
    if annotation is type(None):
        return {"type": "null"}
    if origin in (Union, types.UnionType):
        return {
            "anyOf": [
                _build_type_schema(argument, definitions) for argument in arguments
            ]
        }
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
            "items": [
                _build_value_schema(argument, definitions) for argument in arguments
            ],
            "minItems": len(arguments),
            "maxItems": len(arguments),
        }
    if annotation in (list, tuple, collections.abc.Sequence) or origin in (
        list,
        tuple,
        collections.abc.Sequence,
    ):
        items = _build_value_schema(arguments[0], definitions) if arguments else {}
        return {"type": "array", "items": items}
    if annotation in (dict, collections.abc.Mapping) or origin in (
        dict,
        collections.abc.Mapping,
    ):
        values = _build_value_schema(arguments[1], definitions) if arguments else {}
        return {"type": "object", "additionalProperties": values}
    if isinstance(annotation, type) and is_typeddict(annotation):
        return {"type": "object"}
    if isinstance(annotation, type) and dataclasses.is_dataclass(annotation):
        return {"$ref": f"#/definitions/{_add_definition(annotation, definitions)}"}
    if isinstance(annotation, type):
        return _build_object_schema(annotation, definitions)
    if isinstance(origin, type):
        return _build_object_schema(origin, definitions)
    return {}


def _build_object_schema(cls: Any, definitions: dict[str, Any]) -> dict[str, Any]:
    schema = find_schema(cls) if isinstance(cls, type) else None
    if schema is None:
        return {"type": "object"}
    return {
        "type": "object",
        "if": {
            "properties": {
                CLASS_KEY: {"const": f"{cls.__module__}.{cls.__qualname__}"}
            },
            "required": [CLASS_KEY],
        },
        "then": {"$ref": f"#/definitions/{_add_definition(schema, definitions)}"},
    }


def _add_definition(dataclass: type, definitions: dict[str, Any]) -> str:
    name = f"{dataclass.__module__}.{dataclass.__qualname__}"
    if name not in definitions:
        definitions[name] = {}
        definitions[name] = _build_mapping_schema(dataclass, definitions)
    return name


def _build_mapping_schema(
    dataclass: type, definitions: dict[str, Any]
) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            name: _build_value_schema(annotation, definitions)
            for name, (_, annotation) in classify_fields(dataclass).items()
        },
        "patternProperties": {r"^\$": {}},
        "additionalProperties": False,
    }
