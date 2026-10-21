import dataclasses
import functools
import re
from typing import Any

from omegaconf import MISSING, OmegaConf
from omegaconf.errors import OmegaConfBaseException

from omegakit._core.errors import ConfigSchemaError, SchemaDefinitionError
from omegakit._core.utils.describe import describe_error

from .annotations import find_key_annotation, resolve_aliases
from .fields import read_fields


def convert_plain_values(
    schema: type, values: dict[str, Any], full_key: str
) -> dict[str, Any]:
    """Convert the values of the plain-value fields of a schema with OmegaConf.

    Args:
        schema: The `TypedDict` or dataclass.
        values: The values of its plain-value fields, by name.
        full_key: The full key of the mapping, for errors.

    Returns:
        The converted values, by name.

    Raises:
        ConfigSchemaError: If a value does not match its field.
    """
    structure = _make_plain_values_dataclass(schema)
    escaped_values = {
        key: _escape_omegaconf_syntax(value) for key, value in values.items()
    }
    try:
        typed_values = OmegaConf.structured(structure(**escaped_values))
        # Resolving decodes the escaped texts again
        converted_values: Any = OmegaConf.to_container(typed_values, resolve=True)
    # A number that is too large for a `float` raises an `OverflowError`
    except (OmegaConfBaseException, OverflowError) as error:
        # The key of the value within the mapping, such as `betas[1]`
        value_key = getattr(error, "full_key", None)
        if value_key:
            full_key = f"{full_key}.{value_key}" if full_key else value_key
        raise ConfigSchemaError(
            f"The value does not match `{schema.__qualname__}`: "
            f"{describe_error(error)}",
            full_key,
        ) from error
    return {key: converted_values[key] for key in values}


def convert_value(annotation: Any, value: Any) -> Any:
    """Convert a value to an annotation with OmegaConf.

    Args:
        annotation: The annotation, which `is_plain_value` accepts.
        value: The value.

    Returns:
        The converted value.

    Raises:
        ConfigSchemaError: If `value` does not match `annotation`.
    """
    try:
        structure = _make_single_value_dataclass(annotation)
    # An annotation that cannot be hashed, such as `Literal[[1, 2]]`
    except TypeError:
        structure = _make_single_value_dataclass.__wrapped__(annotation)
    try:
        typed_item = OmegaConf.structured(
            structure(item=_escape_omegaconf_syntax(value))
        )
        converted_item: Any = OmegaConf.to_container(typed_item, resolve=True)
    except (OmegaConfBaseException, OverflowError) as error:
        raise ConfigSchemaError(
            f"The item does not match `{annotation}`: {describe_error(error)}"
        ) from error
    return converted_item["item"]


def convert_keys(annotation: Any, keys: list[Any]) -> list[Any]:
    """Convert the keys of a mapping to the key annotation of its `dict`.

    Args:
        annotation: The annotation of the mapping.
        keys: The keys.

    Returns:
        The converted keys, or `keys` itself if `annotation` has no key annotation.

    Raises:
        SchemaDefinitionError: If OmegaConf does not support the key annotation.
        ConfigSchemaError: If a key does not match the key annotation.
    """
    key_annotation = find_key_annotation(annotation)
    if key_annotation is None or key_annotation is Any:
        return keys
    try:
        structure = _make_single_value_dataclass(dict[key_annotation, Any])
        typed_item = OmegaConf.structured(structure(item=dict.fromkeys(keys)))
        converted_item: Any = OmegaConf.to_container(typed_item)
    # OmegaConf asserts that the type of a key is a class
    except (AssertionError, TypeError) as error:
        raise SchemaDefinitionError(
            f"`{annotation}` has keys that OmegaConf does not support. A key is a "
            "`str`, a number, a `bool` or an `Enum`."
        ) from error
    except OmegaConfBaseException as error:
        raise ConfigSchemaError(
            f"The keys do not match `{annotation}`: {describe_error(error)}"
        ) from error
    return list(converted_item["item"])


def _escape_omegaconf_syntax(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _escape_omegaconf_syntax(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return type(value)(_escape_omegaconf_syntax(item) for item in value)
    if not isinstance(value, str):
        return value
    # OmegaConf would read a resolved text as an interpolation or as `???` again
    escaped_value = re.sub(r"(\\*)\$\{", r"\1\1\\${", value)
    if re.fullmatch(r"\\*\?\?\?", escaped_value):
        return f"\\{escaped_value}"
    return escaped_value


@functools.cache
def _make_plain_values_dataclass(schema: type) -> type:
    # Every field has a default, so that the given values alone make an instance
    data_fields = [
        (name, resolve_aliases(field.annotation), dataclasses.field(default=MISSING))
        for name, field in read_fields(schema).items()
        if field.is_plain_value
    ]
    return dataclasses.make_dataclass(schema.__name__, data_fields)


@functools.cache
def _make_single_value_dataclass(annotation: Any) -> type:
    return dataclasses.make_dataclass("Item", [("item", resolve_aliases(annotation))])
