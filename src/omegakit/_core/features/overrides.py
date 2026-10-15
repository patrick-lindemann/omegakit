from typing import Any, overload

from omegaconf import DictConfig, ListConfig, OmegaConf
from omegaconf.errors import OmegaConfBaseException

from omegakit._core.errors import (
    ConfigOverrideError,
)
from omegakit._core.utils.copy import copy_with_root
from omegakit._core.utils.describe import describe_error
from omegakit._core.utils.walk import walk

from .include import INCLUDE_KEY


@overload
def apply_overrides(
    config: DictConfig,
    overrides: DictConfig | dict[str, Any] | list[str],
    copy: bool = True,
) -> DictConfig: ...


@overload
def apply_overrides(
    config: ListConfig, overrides: ListConfig | list[Any], copy: bool = True
) -> ListConfig: ...


def apply_overrides(
    config: DictConfig | ListConfig,
    overrides: DictConfig | ListConfig | dict[str, Any] | list[Any],
    copy: bool = True,
) -> DictConfig | ListConfig:
    """Apply overrides to a config.

    A mapping merges into a mapping config. A list replaces the items of a list
    config. A list of `key=value` strings applies the items in order to a mapping
    config.

    Args:
        config: The config to override.
        overrides: The mapping, list or `key=value` strings to apply.
        copy: Whether to leave `config` unchanged. Defaults to `True`.

    Returns:
        The config with the overrides applied.

    Raises:
        ConfigOverrideError: If the overrides cannot be parsed or applied.
    """
    if copy:
        config = copy_with_root(config)
    is_dict = isinstance(config, DictConfig)
    if is_dict and isinstance(overrides, list):
        # One at a time, so that a later `key=value` wins over an earlier one
        for item in overrides:
            parsed_item = _parse_dotlist_item(item)
            try:
                config.merge_with(parsed_item)
            except (OmegaConfBaseException, ValueError) as error:
                raise ConfigOverrideError(
                    f"Cannot apply `{item}`: {describe_error(error)}"
                ) from error
        return config
    expected_types = (DictConfig, dict) if is_dict else (ListConfig, list)
    if not isinstance(overrides, expected_types):
        raise ConfigOverrideError(
            f"Cannot override a `{type(config).__name__}` with a "
            f"`{type(overrides).__name__}`."
        )
    try:
        config.merge_with(overrides)
    except (OmegaConfBaseException, ValueError) as error:
        full_key = getattr(error, "full_key", None)
        key = f" at `{full_key}`" if full_key else ""
        raise ConfigOverrideError(
            f"Cannot apply the overrides{key}: {describe_error(error)}"
        ) from error
    return config


def _parse_dotlist_item(item: Any) -> DictConfig:
    if not isinstance(item, str):
        raise ConfigOverrideError(
            f"An override in a list must be a `key=value` string, not `{item!r}`."
        )
    key, separator, _ = item.partition("=")
    if not separator or not key:
        raise ConfigOverrideError(
            f"`{item}` is not an override: write it as `key=value`."
        )
    if "[" in key:
        raise ConfigOverrideError(
            f"`{item}` names an item of a list, which an override cannot set. Give "
            "the whole list instead, as in `key=[1, 2]`."
        )
    try:
        parsed_item = OmegaConf.from_dotlist([item])
    # PyYAML and OmegaConf raise assorted builtin errors for an invalid item
    except Exception as error:
        raise ConfigOverrideError(
            f"Cannot parse `{item}`: {describe_error(error)}"
        ) from error
    for node in walk(parsed_item):
        value = node._value()
        if isinstance(value, str) and value.split(maxsplit=1)[:1] == [INCLUDE_KEY]:
            raise ConfigOverrideError(
                f"`{item}` cannot include a file: the includes are resolved before "
                "the overrides are applied."
            )
    return parsed_item
