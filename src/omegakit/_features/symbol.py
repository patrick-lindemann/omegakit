from typing import Any

from omegaconf import DictConfig, OmegaConf
from omegaconf.errors import InterpolationResolutionError, MissingMandatoryValue

from omegakit._core.error import OmegaKitBaseException
from omegakit._core.locate import locate
from omegakit._utils.describe import describe_error

from .meta import META_KEY

SYMBOL_KEY = "$symbol"


class ConfigSymbolError(OmegaKitBaseException):
    pass


class SymbolSyntaxError(ConfigSymbolError, ValueError):
    pass


class SymbolTypeError(ConfigSymbolError, TypeError):
    pass


class SymbolInterpolationError(ConfigSymbolError, InterpolationResolutionError):
    pass


class SymbolMissingValueError(ConfigSymbolError, MissingMandatoryValue):
    pass


def import_symbol(node: DictConfig) -> Any:
    if SYMBOL_KEY not in node.keys():  # noqa: SIM118
        raise SymbolSyntaxError(f"The node has no `{SYMBOL_KEY}`.")
    other_keys = [key for key in node.keys() if key not in (SYMBOL_KEY, META_KEY)]  # noqa: SIM118
    if other_keys:
        raise SymbolSyntaxError(
            f"A `{SYMBOL_KEY}` cannot stand next to other keys, but there is "
            f"{', '.join(f'`{key}`' for key in other_keys)}."
        )
    if OmegaConf.is_missing(node, SYMBOL_KEY):
        raise SymbolMissingValueError(f"`{SYMBOL_KEY}` holds `???`.")
    try:
        # Resolves an interpolation, as in `$symbol: ${loss}`
        path = node[SYMBOL_KEY]
    except InterpolationResolutionError as error:
        raise SymbolInterpolationError(
            f"Cannot resolve `{SYMBOL_KEY}`: {describe_error(error)}"
        ) from error
    if not isinstance(path, str):
        raise SymbolTypeError(
            f"`{SYMBOL_KEY}` must be an import path, such as `package.module.Name`, "
            f"not `{path!r}`."
        )
    return locate(path)
