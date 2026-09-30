import dataclasses
import functools
from typing import Any

from omegaconf import OmegaConf, SCMode
from omegaconf.errors import OmegaConfBaseException

from omegakit.core.errors import (
    ConfigValidationError,
    OmegaKitBaseException,
    SchemaDefinitionError,
)
from omegakit.core.utils import describe_error, format_full_key, format_path

from .field import classify_fields
from .schema import Schema
from .structure import derive_structure


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
        structure = OmegaConf.structured(derive_structure(schema))
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


@functools.cache
def _find_defaulted_fields(schema: Schema) -> frozenset[str]:
    return frozenset(
        field.name
        for field in dataclasses.fields(schema)
        if field.default is not dataclasses.MISSING
        or field.default_factory is not dataclasses.MISSING
    )
