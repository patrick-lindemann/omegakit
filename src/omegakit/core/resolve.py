from typing import Any

from omegaconf import MISSING, DictConfig, ListConfig, OmegaConf
from omegaconf.errors import (
    InterpolationKeyError,
    InterpolationToMissingValueError,
    MissingMandatoryValue,
)


def resolve_container(
    container: DictConfig | ListConfig, allow_missing: bool = False
) -> Any:
    """Resolve a config into plain containers.

    Args:
        container: The config to resolve.
        allow_missing: Give `???` for missing values and for interpolations to
            missing or unknown keys, instead of raising. Defaults to `False`.

    Returns:
        The resolved config as `dict`s and `list`s.

    Raises:
        OmegaConfBaseException: If a value cannot be resolved, including an
            exception from a resolver.
    """  # noqa: DOC502
    if not allow_missing:
        return OmegaConf.to_container(container, resolve=True, throw_on_missing=True)
    if isinstance(container, ListConfig):
        return [resolve_item(container, index) for index in range(len(container))]
    return {key: resolve_item(container, key) for key in container}


def resolve_item(container: Any, key: Any) -> Any:
    """Resolve one item of a container, giving `???` for a missing value.

    Args:
        container: The `DictConfig` or `ListConfig`.
        key: The item's key or index.

    Returns:
        The resolved item, with containers as `dict`s and `list`s, or `???` for a
        missing value and for an interpolation to a missing or unknown key.
    """
    try:
        value = container[key]
    except (
        MissingMandatoryValue,
        InterpolationToMissingValueError,
        InterpolationKeyError,
    ):
        return MISSING
    if isinstance(value, (DictConfig, ListConfig)):
        return resolve_container(value, allow_missing=True)
    return value
