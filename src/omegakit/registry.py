import inspect
import os
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


# The values that `${secret:...}` has given in this process, so that the command
# line can mask them wherever they appear.
SECRET_VALUES: set[str] = set()


def read_secret(name: str) -> str:
    """Read the environment variable of `${secret:NAME}`, and remember its value.

    Args:
        name: The name of the environment variable.

    Returns:
        The value of the variable.

    Raises:
        ValueError: If the variable is not set.
    """
    try:
        value = os.environ[name]
    except KeyError:
        raise ValueError(f"Environment variable `{name}` is not set.") from None
    SECRET_VALUES.add(value)
    return value
