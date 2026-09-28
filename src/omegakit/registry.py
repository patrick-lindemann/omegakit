import inspect
from collections.abc import Callable
from typing import Any

from omegaconf import OmegaConf


def register_resolver(
    name: str, resolver: Callable[..., Any], replace: bool = False
) -> None:
    """Register a cached OmegaConf resolver on every supported OmegaConf version.

    Args:
        name: The resolver name, as used in `${name:...}`.
        resolver: The resolver function.
        replace: Replace a resolver of the same name. Defaults to `False`.
    """
    # OmegaConf 2.4 deprecates `register_new_resolver`; in 2.3, `register_resolver`
    # is an older, incompatible function.
    register: Any = OmegaConf.register_resolver
    if "replace" in inspect.signature(register).parameters:
        register(
            name,
            resolver,
            replace=replace,
            use_cache=True,
            annotation_validation="off",
        )
    else:
        OmegaConf.register_new_resolver(name, resolver, replace=replace, use_cache=True)
