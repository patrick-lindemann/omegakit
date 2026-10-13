from typing import Any

from omegaconf import DictConfig, OmegaConf
from omegaconf.errors import InterpolationResolutionError, MissingMandatoryValue

from omegakit._core.error import OmegaKitBaseException
from omegakit._core.target import import_target
from omegakit._utils.describe import describe_error

from .meta import META_KEY

REF_KEY = "$ref"


class ConfigRefError(OmegaKitBaseException):
    pass


class RefSyntaxError(ConfigRefError, ValueError):
    pass


class RefTypeError(ConfigRefError, TypeError):
    pass


class RefInterpolationError(ConfigRefError, InterpolationResolutionError):
    pass


class RefMissingValueError(ConfigRefError, MissingMandatoryValue):
    pass


def import_ref(node: DictConfig) -> Any:
    if REF_KEY not in node.keys():  # noqa: SIM118
        raise RefSyntaxError(f"The node has no `{REF_KEY}`.")
    other_keys = [key for key in node.keys() if key not in (REF_KEY, META_KEY)]  # noqa: SIM118
    if other_keys:
        raise RefSyntaxError(
            f"A `{REF_KEY}` cannot stand next to other keys, but there is "
            f"{', '.join(f'`{key}`' for key in other_keys)}."
        )
    if OmegaConf.is_missing(node, REF_KEY):
        raise RefMissingValueError(f"`{REF_KEY}` holds `???`.")
    try:
        # Resolves an interpolation, as in `$ref: ${loss}`
        import_path = node[REF_KEY]
    except InterpolationResolutionError as error:
        raise RefInterpolationError(
            f"Cannot resolve `{REF_KEY}`: {describe_error(error)}"
        ) from error
    if not isinstance(import_path, str):
        raise RefTypeError(
            f"`{REF_KEY}` must be an import path, such as `package.module.Name`, "
            f"not `{import_path!r}`."
        )
    return import_target(import_path)
