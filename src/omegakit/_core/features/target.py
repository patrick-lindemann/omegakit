from dataclasses import dataclass
from typing import Any

from omegaconf import DictConfig

from omegakit._core.errors import ConfigTargetError, ConfigValidationError
from omegakit._core.utils.locate import locate
from omegakit._core.utils.read import read_value

from .meta import META_KEY
from .symbol import SYMBOL_KEY

TARGET_KEY = "$target"
PARTIAL_KEY = "$partial"
ARGS_KEY = "$args"


@dataclass(frozen=True)
class TargetArguments:
    is_partial: bool
    keys: list[Any]
    has_args: bool


def import_target(node: DictConfig) -> Any:
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
