from typing import Any

from .config import Config, cast_config
from .errors import ConfigValidationError
from .typecheck import check


def validate(  # noqa: DOC502
    config: Config | dict[Any, Any] | list[Any] | tuple[Any, ...],
    schema: type | None = None,
    *,
    allow_missing: bool = False,
) -> None:
    """Check a config and import what `$target` and `$symbol` name, without calling it.

    A `TypedDict` as `schema` checks a mapping, and a class checks what a `$target`
    node builds.

    Args:
        config: The config, or a `dict`, `list` or `tuple`.
        schema: The type that the config must give. Defaults to `None`, in which case
            only the config itself is checked.
        allow_missing: Whether to accept a `???`, a required key that is not given and
            an interpolation to a missing or unknown key, as in a file that others
            complete. Every other value is still checked. Defaults to `False`.

    Raises:
        ConfigValidationError: If a value is missing and `allow_missing` is `False`,
            a value cannot be resolved, an import path cannot be imported, or a value
            does not match its schema.
        SchemaDefinitionError: If `schema` or the schema of a `$target` cannot check a
            config.
    """
    check(cast_config(config), schema, allow_missing=allow_missing)


def is_valid(  # noqa: DOC502
    config: Config | dict[Any, Any] | list[Any] | tuple[Any, ...],
    schema: type | None = None,
    *,
    allow_missing: bool = False,
) -> bool:
    """Check whether a config passes `validate`.

    A `TypedDict` as `schema` checks a mapping, and a class checks what a `$target`
    node builds.

    Args:
        config: The config, or a `dict`, `list` or `tuple`.
        schema: The type that the config must give. Defaults to `None`, in which case
            only the config itself is checked.
        allow_missing: Whether to accept missing values, as `validate` does. Defaults
            to `False`.

    Returns:
        `True` if `validate` raises no `ConfigValidationError`, else `False`.

    Raises:
        SchemaDefinitionError: If `schema` or the schema of a `$target` cannot check a
            config.
    """
    try:
        validate(config, schema, allow_missing=allow_missing)
    except ConfigValidationError:
        return False
    return True
