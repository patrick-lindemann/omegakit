import dataclasses
import functools
import inspect
import keyword
import types
from dataclasses import dataclass
from typing import Any, NotRequired, Required, get_origin, get_type_hints, is_typeddict

from omegaconf import MISSING

from omegakit._core.configurable import Configurable
from omegakit._core.errors import SchemaDefinitionError
from omegakit._core.utils.describe import describe_error

from .annotations import holds_objects, is_plain_value, union_members


@dataclass(frozen=True)
class SchemaField:
    annotation: Any
    is_plain_value: bool
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
                for field in dataclasses.fields(schema)  # ty: ignore[invalid-argument-type]
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
            member for member in union_members(annotation) if is_typeddict(member)
        ]
        is_plain = is_plain_value(annotation)
        if not name.isidentifier() or keyword.iskeyword(name):
            raise SchemaDefinitionError(
                f"`{name}` of `{schema.__qualname__}` cannot be a key: a key is a "
                "Python identifier."
            )
        if len(sections) > 1:
            raise SchemaDefinitionError(
                f"`{schema.__qualname__}.{name}` is annotated with `{annotation}`, "
                "which names several `TypedDict`s. A field takes at most one."
            )
        if not is_plain and not holds_objects(annotation):
            raise SchemaDefinitionError(
                f"`{schema.__qualname__}.{name}` is annotated with `{annotation}`, "
                "which is neither a type that OmegaConf supports nor a `TypedDict` or "
                "a class."
            )
        fields[name] = SchemaField(annotation, is_plain, is_required)
    return fields


@functools.cache
def read_positional_names(schema: type) -> list[str]:
    parameters = inspect.signature(schema).parameters.values()
    kinds = (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    return [parameter.name for parameter in parameters if parameter.kind in kinds]


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
                origin is not NotRequired and schema.__total__  # ty: ignore[unresolved-attribute]
            )
    return required_keys
