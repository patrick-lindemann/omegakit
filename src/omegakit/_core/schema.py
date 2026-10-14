from typing import Any

from .config import Config, cast_config
from .errors import ConfigValidationError
from .typecheck import check


def validate(  # noqa: DOC502
    config: Config | dict[Any, Any] | list[Any] | tuple[Any, ...],
    schema: type | None = None,
) -> None:
    """Check a config and import what `$target` and `$symbol` name, without calling it.

    A `TypedDict` as `schema` checks a mapping, and a class checks what a `$target`
    node builds.

    Args:
        config: The config, or a `dict`, `list` or `tuple`.
        schema: The type that the config must give. Defaults to `None`, in which case
            only the config itself is checked.

    Raises:
        ConfigValidationError: If a value is `???` or cannot be resolved, an import
            path cannot be imported, or a value does not match its schema.
        SchemaDefinitionError: If `schema` or the schema of a `$target` cannot check a
            config.
    """
    check(cast_config(config), schema)  # ty: ignore[no-matching-overload]


def is_valid(  # noqa: DOC502
    config: Config | dict[Any, Any] | list[Any] | tuple[Any, ...],
    schema: type | None = None,
) -> bool:
    """Check whether a config passes `validate`.

    A `TypedDict` as `schema` checks a mapping, and a class checks what a `$target`
    node builds.

    Args:
        config: The config, or a `dict`, `list` or `tuple`.
        schema: The type that the config must give. Defaults to `None`, in which case
            only the config itself is checked.

    Returns:
        `True` if `validate` raises no `ConfigValidationError`, else `False`.

    Raises:
        SchemaDefinitionError: If `schema` or the schema of a `$target` cannot check a
            config.
    """
    try:
        validate(config, schema)
    except ConfigValidationError:
        return False
    return True
