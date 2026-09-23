from __future__ import annotations

import functools
import importlib
from collections.abc import Callable
from typing import Any

from omegaconf import DictConfig, ListConfig, OmegaConf

from .config import (
    CLASS_KEY,
    META_KEY,
    PARTIAL_KEY,
    REF_KEY,
    _cast_overrides,
)


def instantiate[T](
    config: DictConfig | dict[str, Any],
    type: type[T] = Any,  # noqa: A002 (renamed to `expected` in stage 6)
    overrides: DictConfig | dict[str, Any] | list[str] | None = None,
) -> T:
    """Instantiate an object from a configuration.

    Args:
        config: The configuration.
        type: The expected type of the instantiated object. This is used for type
            checking and does not affect the instantiation process. Defaults to
            `Any`.
        overrides: Additional argument overrides. Can be provided as a DictConfig, a
            regular dictionary, or a list of `key=value` strings (e.g.
            `["foo=1.0", "bar=baz"]`). Defaults to `None`.

    Returns:
        The instantiated object.
    """
    return _instantiate(config, overrides)


def prepare[T](
    config: DictConfig | dict[str, Any],
    type: type[T] = Any,  # noqa: A002 (renamed to `expected` in stage 6)
    overrides: DictConfig | dict[str, Any] | list[str] | None = None,
) -> functools.partial[T]:
    """Prepare an object for instantiation from a configuration.

    The resulting function can be called later to perform the actual instantiation with
    extra arguments.

    Args:
        config: The configuration.
        type: The expected type of the instantiated object. This is used for type
            checking and does not affect the instantiation process. Defaults to
            `Any`.
        overrides: Additional argument overrides. Can be provided as a DictConfig, a
            regular dictionary, or a list of `key=value` strings (e.g.
            `["foo=1.0", "bar=baz"]`). Defaults to `None`.

    Returns:
        The instantiating function.
    """
    return _instantiate(config, overrides, wrap=functools.partial)


def _import_object(import_path: str) -> Any:
    module_path, _, attr_name = import_path.rpartition(".")
    module = importlib.import_module(module_path)
    try:
        return getattr(module, attr_name)
    except AttributeError as error:
        raise ImportError(
            f"Could not import `{attr_name}` from module `{module_path}`. Make sure "
            "the import name is correct, and that dependencies are installed, if "
            "necessary."
        ) from error


def _instantiate(
    config: DictConfig | dict[str, Any],
    overrides: dict[str, Any] | None = None,
    wrap: Callable | None = None,
) -> Any:
    if CLASS_KEY not in config:
        raise ValueError(
            f"Cannot instantiate config with no `{CLASS_KEY}` key:"
            f"\n{OmegaConf.to_yaml(config)}"
        )
    if OmegaConf.is_config(config) or overrides is not None:
        if not OmegaConf.is_config(config):
            config = OmegaConf.create(config)
        if overrides is not None:
            config = config.copy()
            overrides = _cast_overrides(overrides)
            config.merge_with(overrides)

        plain_config = OmegaConf.to_container(
            config, resolve=True, throw_on_missing=True
        )
    else:
        # A plain dict arriving from `_materialize` is already fully resolved
        plain_config = config
    cls = _import_object(plain_config[CLASS_KEY])
    # Recursively materialize the nested config: Instantiating all children containing
    # the class key
    kwargs = {}
    for key, value in plain_config.items():
        if key in (CLASS_KEY, META_KEY):
            continue
        if key == PARTIAL_KEY:
            if value is True:
                wrap = functools.partial
            continue
        kwargs[key] = _materialize(value)
    # Final instantiation
    try:
        if hasattr(cls, "from_config"):
            return (
                wrap(cls.from_config, kwargs)
                if wrap is not None
                else cls.from_config(kwargs)
            )
        return wrap(cls, **kwargs) if wrap is not None else cls(**kwargs)
    except (ValueError, TypeError) as error:
        raise type(error)(
            f"An error occurred while instantiating `{cls.__name__}` from config: "
            f"{error}"
        ) from error


def _materialize(node: Any) -> Any:
    if isinstance(node, (dict, DictConfig)):
        node = {k: v for k, v in node.items() if k != META_KEY}
        if CLASS_KEY in node:
            return _instantiate(node)
        if REF_KEY in node:
            if len(node) > 1:
                raise ValueError(
                    f"Invalid config node with `{REF_KEY}` key: {node}. A node using "
                    f"`{REF_KEY}` cannot contain any other keys."
                )
            return _import_object(node[REF_KEY])
        return {k: _materialize(v) for k, v in node.items()}
    if isinstance(node, (list, ListConfig)):
        return [_materialize(v) for v in node]
    return node
