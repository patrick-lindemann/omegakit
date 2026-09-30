from typing import Any

from omegaconf import DictConfig, ListConfig, OmegaConf

from omegakit.core.errors import ConfigLoadError
from omegakit.core.tree import merge_in_dependency_order
from omegakit.core.utils import format_node_path

DEFAULTS_KEY = "$defaults"
"""A mapping merged underneath every dict-valued sibling."""


def apply_defaults(config: DictConfig | ListConfig) -> None:
    """Merge every `$defaults` under its dict-valued siblings in place.

    Args:
        config: The config to process.

    Raises:
        ConfigLoadError: If a `$defaults` is not a mapping, cannot be resolved,
            or if `$defaults` references form a cycle.
    """  # noqa: DOC502
    merge_in_dependency_order(config, DEFAULTS_KEY, _merge_defaults)


def _merge_defaults(node: DictConfig, defaults: Any) -> None:
    if not isinstance(defaults, DictConfig):
        raise ConfigLoadError(
            f"`{DEFAULTS_KEY}` in `{format_node_path(node)}` is not a mapping."
        )
    node.pop(DEFAULTS_KEY)
    for key, item in list(node.items_ex(resolve=False)):
        if not str(key).startswith("$") and isinstance(item, DictConfig):
            node[key] = OmegaConf.merge(defaults, item)
