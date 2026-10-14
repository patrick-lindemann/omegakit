from typing import Any

from .config import Config, cast_config
from .schema import check


def validate(
    config: Config | dict[Any, Any] | list[Any] | tuple[Any, ...],
    schema: type | None = None,
) -> None:
    check(cast_config(config), schema)
