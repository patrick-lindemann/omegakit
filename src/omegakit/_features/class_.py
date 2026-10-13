from collections.abc import Callable
from typing import Any, NamedTuple

from omegaconf import DictConfig, OmegaConf
from omegaconf.errors import InterpolationResolutionError, MissingMandatoryValue

from omegakit._core.error import OmegaKitBaseException
from omegakit._core.target import import_target
from omegakit._utils.describe import describe_error

from .meta import META_KEY
from .ref import REF_KEY

CLASS_KEY = "$class"
PARTIAL_KEY = "$partial"


class ConfigClassError(OmegaKitBaseException):
    pass


class ClassSyntaxError(ConfigClassError, ValueError):
    pass


class ClassTypeError(ConfigClassError, TypeError):
    pass


class ClassInterpolationError(ConfigClassError, InterpolationResolutionError):
    pass


class ClassMissingValueError(ConfigClassError, MissingMandatoryValue):
    pass


class ClassArguments(NamedTuple):
    is_partial: bool
    keys: list[Any]


def import_class(node: DictConfig) -> Any:
    if CLASS_KEY not in node.keys():  # noqa: SIM118
        raise ClassSyntaxError(f"The node has no `{CLASS_KEY}`.")
    import_path = _read_key(node, CLASS_KEY)
    if not isinstance(import_path, str):
        raise ClassTypeError(
            f"`{CLASS_KEY}` must be an import path, such as `package.module.Name`, "
            f"not `{import_path!r}`."
        )
    target = import_target(import_path)
    if not (callable(target) or hasattr(target, "from_config")):
        raise ClassTypeError(
            f"`{import_path}` is neither callable nor has `from_config`. Use "
            f"`{REF_KEY}` for an object that is used as it is."
        )
    return target


def read_arguments(node: DictConfig) -> ClassArguments:
    keys = [
        key
        for key in node.keys()  # noqa: SIM118
        if key not in (CLASS_KEY, PARTIAL_KEY, META_KEY)
    ]
    reserved_keys = [key for key in keys if str(key).startswith("$")]
    if reserved_keys:
        raise ClassSyntaxError(
            f"{', '.join(f'`{key}`' for key in reserved_keys)} cannot be an argument "
            f"of a `{CLASS_KEY}`: keys that start with `$` are reserved."
        )
    is_partial = False
    if PARTIAL_KEY in node.keys():  # noqa: SIM118
        is_partial = _read_key(node, PARTIAL_KEY)
        if not isinstance(is_partial, bool):
            raise ClassTypeError(
                f"`{PARTIAL_KEY}` must be `true` or `false`, not `{is_partial!r}`."
            )
    return ClassArguments(is_partial, keys)


def make_node(target: Callable[..., Any], /, **kwargs: Any) -> dict[str, Any]:
    qualname = target.__qualname__
    if "." in qualname:
        raise ClassSyntaxError(
            f"Cannot create a node for `{qualname}`: only objects defined at module "
            "level can be imported by their path."
        )
    return {CLASS_KEY: f"{target.__module__}.{qualname}", **kwargs}


def _read_key(node: DictConfig, key: str) -> Any:
    if OmegaConf.is_missing(node, key):
        raise ClassMissingValueError(f"`{key}` holds `???`.")
    try:
        # Resolves an interpolation, as in `$class: ${model_class}`
        return node[key]
    except InterpolationResolutionError as error:
        raise ClassInterpolationError(
            f"Cannot resolve `{key}`: {describe_error(error)}"
        ) from error
