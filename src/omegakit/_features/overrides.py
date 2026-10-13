from typing import Any, overload

from omegaconf import DictConfig, ListConfig, OmegaConf
from omegaconf.errors import OmegaConfBaseException

from omegakit._core.error import OmegaKitBaseException
from omegakit._core.merge import copy_with_root
from omegakit._utils.describe import describe_error


class ConfigOverrideError(OmegaKitBaseException):
    pass


class OverrideSyntaxError(ConfigOverrideError, ValueError):
    pass


class OverrideTypeError(ConfigOverrideError, TypeError):
    pass


class OverrideMergeError(ConfigOverrideError):
    pass


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
    if copy:
        config = copy_with_root(config)
    is_dict = isinstance(config, DictConfig)
    if is_dict and isinstance(overrides, list):
        # One at a time, so that a later `key=value` wins over an earlier one
        for item in overrides:
            parsed_item = _parse_dotlist_item(item)
            apply_overrides(config, parsed_item, copy=False)
        return config
    expected_types = (DictConfig, dict) if is_dict else (ListConfig, list)
    if not isinstance(overrides, expected_types):
        raise OverrideTypeError(
            f"Cannot override a `{type(config).__name__}` with a "
            f"`{type(overrides).__name__}`."
        )
    try:
        config.merge_with(overrides)
    except (OmegaConfBaseException, ValueError) as error:
        full_key = getattr(error, "full_key", None)
        key = f" at `{full_key}`" if full_key else ""
        raise OverrideMergeError(
            f"Cannot apply the overrides{key}: {describe_error(error)}"
        ) from error
    return config


def _parse_dotlist_item(item: Any) -> DictConfig:
    if not isinstance(item, str):
        raise OverrideTypeError(
            f"An override in a list must be a `key=value` string, not `{item!r}`."
        )
    try:
        return OmegaConf.from_dotlist([item])
    # PyYAML and OmegaConf raise assorted builtin errors for an invalid item
    except Exception as error:
        raise OverrideSyntaxError(
            f"Cannot parse `{item}`: {describe_error(error)}"
        ) from error
