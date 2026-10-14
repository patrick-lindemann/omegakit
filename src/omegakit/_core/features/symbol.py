from typing import Any

from omegaconf import DictConfig

from omegakit._core.errors import (
    ConfigSymbolError,
)
from omegakit._core.utils.locate import locate
from omegakit._core.utils.read import read_value

from .meta import META_KEY

SYMBOL_KEY = "$symbol"
"""The key of the import path of an object that replaces its node as it is."""


def import_symbol(node: DictConfig) -> Any:
    if SYMBOL_KEY not in node.keys():  # noqa: SIM118
        raise ConfigSymbolError(f"The node has no `{SYMBOL_KEY}`.")
    other_keys = [key for key in node.keys() if key not in (SYMBOL_KEY, META_KEY)]  # noqa: SIM118
    if other_keys:
        raise ConfigSymbolError(
            f"A `{SYMBOL_KEY}` cannot stand next to other keys, but there is "
            f"{', '.join(f'`{key}`' for key in other_keys)}."
        )
    qualified_name = read_value(node, SYMBOL_KEY)
    if not isinstance(qualified_name, str):
        raise ConfigSymbolError(
            f"`{SYMBOL_KEY}` must be an import path, such as `package.module.Name`, "
            f"not `{qualified_name!r}`."
        )
    return locate(qualified_name)
