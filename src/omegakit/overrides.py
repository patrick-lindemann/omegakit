from typing import Any

from omegaconf import DictConfig, OmegaConf
from omegaconf.errors import OmegaConfBaseException
from yaml import YAMLError

from .errors import (
    ConfigLoadError,
    OmegaKitBaseException,
    describe_error,
    describe_value,
    format_full_key,
)


def merge_overrides(
    config: DictConfig, overrides: DictConfig | dict[str, Any] | list[str]
) -> None:
    """Merge overrides into a config in place.

    Args:
        config: The config to change.
        overrides: A `DictConfig`, a dictionary, or a list of `key=value` strings.

    Raises:
        ConfigLoadError: If an override does not parse, has a value of an
            unsupported type, or is rejected by `config`.
        TypeError: If `overrides` is not a `DictConfig`, a `dict` or a `list`, or a
            list item is not a string.
    """  # noqa: DOC503
    try:
        parsed_overrides = _parse_overrides(overrides)
        config.merge_with(parsed_overrides)
    except OmegaConfBaseException as error:
        if isinstance(error, OmegaKitBaseException):
            raise
        else:
            location = f" `{format_full_key(error.full_key)}`" if error.full_key else ""
            raise ConfigLoadError(
                f"Cannot apply the override{location}: {describe_error(error)}"
            ) from error


def _parse_overrides(
    overrides: DictConfig | dict[str, Any] | list[str],
) -> DictConfig:
    if isinstance(overrides, DictConfig):
        return overrides
    elif isinstance(overrides, dict):
        return OmegaConf.create(overrides)
    elif isinstance(overrides, list):
        parsed = OmegaConf.create()
        for override in overrides:
            if not isinstance(override, str):
                raise TypeError(
                    "An override in a list must be a `key=value` string, not "
                    f"{describe_value(override)}."
                )
            try:
                parsed.merge_with_dotlist([override])
            except (YAMLError, OmegaConfBaseException) as error:
                raise ConfigLoadError(
                    f"Cannot parse the override `{override}`: {describe_error(error)}"
                ) from error
        return parsed
    else:
        raise TypeError(
            f"Unsupported overrides type: {type(overrides)}. Expected a `DictConfig`, "
            "a `dict` or a `list` of `key=value` strings."
        )
