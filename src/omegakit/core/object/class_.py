import functools
from collections.abc import Callable
from typing import Any

from omegakit.core.errors import ConfigValidationError
from omegakit.core.utils import describe_value, format_path

from ._target import import_target
from .ref import REF_KEY

CLASS_KEY = "$class"
"""Import path of the class or function a node is built with."""

PARTIAL_KEY = "$partial"
"""Flag that builds a `functools.partial` instead of calling the class."""


def make_node(target: Callable[..., Any], /, **kwargs: Any) -> dict[str, Any]:
    """Create an instantiable config node for a class or function.

    Args:
        target: The class or function to build. It must be defined at module level.
        **kwargs: The node's arguments.

    Returns:
        The node: `kwargs` plus `$class` set to the import path of `target`.

    Raises:
        ValueError: If `target` is defined inside a function or a class, where it
            cannot be imported by its path.
    """
    qualname = target.__qualname__
    if "." in qualname:
        raise ValueError(
            f"Cannot create a node for `{qualname}`: only objects defined at module "
            "level can be imported by their path."
        )
    return {CLASS_KEY: f"{target.__module__}.{qualname}", **kwargs}


def import_class(
    node: dict[str, Any],
    path: tuple[str | int, ...],
    allowed_modules: tuple[str, ...] | None,
) -> Any:
    """Import the class or function that a `$class` node names.

    Args:
        node: The resolved node.
        path: The node's path from the config root.
        allowed_modules: The modules that `$class` may name, as in `import_target`.

    Returns:
        The imported class or function.

    Raises:
        ConfigValidationError: If the object cannot be imported as `import_target`
            says, or is neither callable nor has `from_config`.
        ImportError: If the named module fails to import a module of its own.
    """  # noqa: DOC503
    target = import_target(node, CLASS_KEY, path, allowed_modules)
    if not (callable(target) or hasattr(target, "from_config")):
        raise ConfigValidationError(
            f"`{CLASS_KEY}: {node[CLASS_KEY]}` in `{format_path(path)}` is neither "
            f"callable nor has `from_config`. Use `{REF_KEY}` for an object that is "
            "used as it is."
        )
    return target


def split_arguments(
    node: dict[str, Any], path: tuple[str | int, ...]
) -> tuple[bool, dict[str, Any]]:
    """Split a `$class` node into its `$partial` flag and its arguments.

    Args:
        node: The resolved node.
        path: The node's path from the config root.

    Returns:
        The value of `$partial`, `False` if it is not given, and the other keys
        without `$class`.

    Raises:
        ConfigValidationError: If `$partial` is not a boolean, or the node has
            another key that starts with `$`.
    """
    partial = False
    arguments = {}
    for key, value in node.items():
        if key == CLASS_KEY:
            continue
        if key == PARTIAL_KEY:
            if not isinstance(value, bool):
                raise ConfigValidationError(
                    f"`{PARTIAL_KEY}` in `{format_path(path)}` must be `true` or "
                    f"`false`, but the config gives {describe_value(value)}."
                )
            partial = value
            continue
        if isinstance(key, str) and key.startswith("$"):
            raise ConfigValidationError(
                f"Key `{key}` in `{format_path(path)}` is not supported next to "
                f"`{CLASS_KEY}`; keys starting with `$` are reserved."
            )
        arguments[key] = value
    return partial, arguments


def call(
    target: Any,
    config: Any,
    partial: bool,
    path: tuple[str | int, ...],
    name: str,
) -> Any:
    """Build the object of a `$class` node from its built config.

    Args:
        target: The class or function.
        config: The config that `from_config` takes, or the keyword arguments of
            `target` if it has no `from_config`.
        partial: Return a `functools.partial` instead of calling `target`.
        path: The node's path from the config root.
        name: The import path of `target`, for the note on an error.

    Returns:
        The built object, or the partial that builds it.

    Raises:
        Exception: Whatever `target` raises, with a note that names the node.
    """  # noqa: DOC502
    try:
        if hasattr(target, "from_config"):
            if partial:
                return functools.partial(target.from_config, config)
            return target.from_config(config)
        return functools.partial(target, **config) if partial else target(**config)
    except Exception as error:
        error.add_note(f"while instantiating {format_path(path)} ({name})")
        raise
