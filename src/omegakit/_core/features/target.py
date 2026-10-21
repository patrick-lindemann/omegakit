from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from omegaconf import DictConfig

from omegakit._core.errors import ConfigTargetError, ConfigValidationError
from omegakit._core.utils.locate import locate
from omegakit._core.utils.read import read_value

from .meta import META_KEY
from .symbol import SYMBOL_KEY

TARGET_KEY = "$target"
"""The key of the import path of the class or function that builds its node."""
PARTIAL_KEY = "$partial"
"""The key that, set to `true`, builds a partial of the `$target` instead."""
ARGS_KEY = "$args"
"""The key of the list of positional arguments of the `$target`."""


@dataclass(frozen=True)
class TargetArguments:
    """The keys of a `$target` node besides `$target`.

    These are the argument keys, `$partial`, and whether `$args` is given.
    """

    is_partial: bool
    keys: list[Any]
    has_args: bool


def import_target(node: DictConfig) -> Any:
    """Import the class or function that a `$target` node names.

    Args:
        node: The node.

    Returns:
        The class or function.

    Raises:
        ConfigTargetError: If the node has no `$target`, its `$target` is no `str`,
            or the object is neither callable nor has `from_config`.
    """
    if TARGET_KEY not in node.keys():  # noqa: SIM118
        raise ConfigTargetError(f"The node has no `{TARGET_KEY}`.")
    qualified_name = read_value(node, TARGET_KEY)
    if not isinstance(qualified_name, str):
        raise ConfigTargetError(
            f"`{TARGET_KEY}` must be an import path, such as `package.module.Name`, "
            f"not `{qualified_name!r}`."
        )
    target = locate(qualified_name)
    if not (callable(target) or hasattr(target, "from_config")):
        raise ConfigTargetError(
            f"`{qualified_name}` is neither callable nor has `from_config`. Use "
            f"`{SYMBOL_KEY}` for an object that is used as it is."
        )
    return target


def read_arguments(node: DictConfig) -> TargetArguments:
    """Read and check the arguments of a `$target` node.

    Args:
        node: The node.

    Returns:
        The arguments.

    Raises:
        ConfigValidationError: If an argument key starts with `$`.
        ConfigTargetError: If `$partial` is not a `bool`.
    """
    node_keys = list(node.keys())
    keys = [
        key
        for key in node_keys
        if key not in (TARGET_KEY, PARTIAL_KEY, ARGS_KEY, META_KEY)
    ]
    reserved_keys = [key for key in keys if str(key).startswith("$")]
    if reserved_keys:
        raise ConfigValidationError(
            f"{', '.join(f'`{key}`' for key in reserved_keys)} cannot be an argument "
            f"of a `{TARGET_KEY}`: keys that start with `$` are reserved."
        )
    is_partial = False
    if PARTIAL_KEY in node_keys:
        is_partial = read_value(node, PARTIAL_KEY)
        if not isinstance(is_partial, bool):
            raise ConfigTargetError(
                f"`{PARTIAL_KEY}` must be `true` or `false`, not `{is_partial!r}`."
            )
    return TargetArguments(is_partial, keys, ARGS_KEY in node_keys)


def make_node(
    target: Callable[..., Any], /, *args: Any, **kwargs: Any
) -> dict[str, Any]:
    """Make a config node that calls a class or function.

    The node holds the import path of `target` under `$target`, the positional
    arguments under `$args` and the keyword arguments as keys.

    Args:
        target: A class or function defined at module level.
        *args: The positional arguments.
        **kwargs: The keyword arguments.

    Returns:
        The node as a `dict`.

    Raises:
        ConfigTargetError: If `target` cannot be imported by its path, such as a nested
            class or a `functools.partial`.
    """
    # A callable object, such as a `functools.partial`, has no name of its own
    qualname = getattr(target, "__qualname__", None)
    if qualname is None or "." in qualname:
        raise ConfigTargetError(
            f"Cannot create a node for `{qualname or target!r}`: only objects "
            "defined at module level can be imported by their path."
        )
    node = {TARGET_KEY: f"{target.__module__}.{qualname}", **kwargs}
    if args:
        node[ARGS_KEY] = list(args)
    return node
