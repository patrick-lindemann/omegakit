import dataclasses
import functools
import inspect
import keyword
from dataclasses import dataclass
from typing import Any

from omegaconf import MISSING
from typing_extensions import get_type_hints, is_typeddict

from omegakit._core.configurable import Configurable
from omegakit._core.errors import SchemaDefinitionError
from omegakit._core.utils.describe import describe_error

from .annotations import find_required_mark, holds_objects, is_class, is_plain_value


@dataclass(frozen=True)
class SchemaField:
    """A field of a `TypedDict` or dataclass schema."""

    annotation: Any
    is_plain_value: bool
    is_required: bool


def find_schema(target: Any) -> type | None:
    """Find the schema that checks the arguments of a `$target`.

    Args:
        target: The class or function.

    Returns:
        The `schema` of a `Configurable`, `target` itself if it is a dataclass, or
        `None`.

    Raises:
        SchemaDefinitionError: If the `schema` of `target` is not a `TypedDict`.
    """
    if not is_class(target):
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
    """Read and check the fields of a schema.

    Args:
        schema: The `TypedDict` or dataclass.

    Returns:
        The fields, by name.

    Raises:
        SchemaDefinitionError: If an annotation cannot be read, a name is no Python
            identifier, or an annotation cannot be checked.
    """
    try:
        annotations = get_type_hints(schema)
        if dataclasses.is_dataclass(schema):
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
        else:
            required_keys = _read_required_keys(schema)
    # Evaluating an annotation runs arbitrary code, which can raise anything
    except Exception as error:
        raise SchemaDefinitionError(
            f"Cannot read the annotations of `{schema.__qualname__}`: "
            f"{describe_error(error)}"
        ) from error
    fields = {}
    for name, is_required in required_keys.items():
        annotation = annotations[name]
        is_plain = is_plain_value(annotation)
        if not name.isidentifier() or keyword.iskeyword(name):
            raise SchemaDefinitionError(
                f"`{name}` of `{schema.__qualname__}` cannot be a key: a key is a "
                "Python identifier."
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
    """Read the names of the parameters that can be given by position.

    Args:
        schema: The class or function.

    Returns:
        The names, in order.
    """
    parameters = inspect.signature(schema).parameters.values()
    kinds = (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    return [parameter.name for parameter in parameters if parameter.kind in kinds]


def _read_required_keys(schema: type) -> dict[str, bool]:
    # `__required_keys__` misses a `Required` or `NotRequired` written as text
    annotations = get_type_hints(schema, include_extras=True)
    required_keys: dict[str, bool] = {}
    for name, annotation in annotations.items():
        mark = find_required_mark(annotation)
        required_keys[name] = (
            name in schema.__required_keys__  # ty: ignore[unresolved-attribute]
            if mark is None
            else mark
        )
    return required_keys
