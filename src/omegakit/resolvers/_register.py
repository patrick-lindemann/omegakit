from collections.abc import Callable
from typing import Any

from omegaconf import OmegaConf


def register_resolver(
    name: str, resolver: Callable[..., Any], *, replace: bool = False
) -> None:
    """Register a cached OmegaConf resolver.

    Args:
        name: The resolver name, as used in `${name:...}`.
        resolver: The resolver function.
        replace: Replace a resolver of the same name. Defaults to `False`.

    Raises:
        ValueError: If a resolver named `name` exists and `replace` is `False`.
    """  # noqa: DOC502
    OmegaConf.register_resolver(
        name, resolver, replace=replace, use_cache=True, annotation_validation="off"
    )
