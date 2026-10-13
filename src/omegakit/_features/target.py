from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from omegaconf import DictConfig, OmegaConf
from omegaconf.errors import InterpolationResolutionError, MissingMandatoryValue

from omegakit._core.error import OmegaKitBaseException
from omegakit._utils.describe import describe_error
from omegakit._utils.locate import locate

from .meta import META_KEY
from .symbol import SYMBOL_KEY

TARGET_KEY = "$target"
PARTIAL_KEY = "$partial"
ARGS_KEY = "$args"


class ConfigTargetError(OmegaKitBaseException):
    pass


class TargetSyntaxError(ConfigTargetError, ValueError):
    pass


class TargetTypeError(ConfigTargetError, TypeError):
    pass


class TargetInterpolationError(ConfigTargetError, InterpolationResolutionError):
    pass


class TargetMissingValueError(ConfigTargetError, MissingMandatoryValue):
    pass


@dataclass(frozen=True)
class TargetArguments:
    is_partial: bool
    keys: list[Any]
    has_args: bool


def import_target(node: DictConfig) -> Any:
    if TARGET_KEY not in node.keys():  # noqa: SIM118
        raise TargetSyntaxError(f"The node has no `{TARGET_KEY}`.")
    qualified_name = _read_key(node, TARGET_KEY)
    if not isinstance(qualified_name, str):
        raise TargetTypeError(
            f"`{TARGET_KEY}` must be an import path, such as `package.module.Name`, "
            f"not `{qualified_name!r}`."
        )
    target = locate(qualified_name)
    if not (callable(target) or hasattr(target, "from_config")):
        raise TargetTypeError(
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
        raise TargetSyntaxError(
            f"{', '.join(f'`{key}`' for key in reserved_keys)} cannot be an argument "
            f"of a `{TARGET_KEY}`: keys that start with `$` are reserved."
        )
    is_partial = False
    if PARTIAL_KEY in node_keys:
        is_partial = _read_key(node, PARTIAL_KEY)
        if not isinstance(is_partial, bool):
            raise TargetTypeError(
                f"`{PARTIAL_KEY}` must be `true` or `false`, not `{is_partial!r}`."
            )
    return TargetArguments(is_partial, keys, ARGS_KEY in node_keys)


def make_node(
    target: Callable[..., Any], /, *args: Any, **kwargs: Any
) -> dict[str, Any]:
    qualname = target.__qualname__
    if "." in qualname:
        raise TargetSyntaxError(
            f"Cannot create a node for `{qualname}`: only objects defined at module "
            "level can be imported by their path."
        )
    node = {TARGET_KEY: f"{target.__module__}.{qualname}", **kwargs}
    if args:
        node[ARGS_KEY] = list(args)
    return node


def _read_key(node: DictConfig, key: str) -> Any:
    if OmegaConf.is_missing(node, key):
        raise TargetMissingValueError(f"`{key}` holds `???`.")
    try:
        # Resolves an interpolation, as in `$target: ${model}`
        return node[key]
    except InterpolationResolutionError as error:
        raise TargetInterpolationError(
            f"Cannot resolve `{key}`: {describe_error(error)}"
        ) from error
