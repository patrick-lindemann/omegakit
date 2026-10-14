from typing import Any

from .config import Config, cast_config
from .errors import ConfigValidationError
from .typecheck import check


def validate(
    config: Config | dict[Any, Any] | list[Any] | tuple[Any, ...],
    schema: type | None = None,
) -> None:
    check(cast_config(config), schema)  # ty: ignore[no-matching-overload]


def is_valid(
    config: Config | dict[Any, Any] | list[Any] | tuple[Any, ...],
    schema: type | None = None,
) -> bool:
    try:
        validate(config, schema)
    except ConfigValidationError:
        return False
    return True
