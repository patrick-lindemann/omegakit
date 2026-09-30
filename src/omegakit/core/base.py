from typing import Any, cast

from omegaconf import DictConfig, ListConfig, OmegaConf

from .errors import ConfigLoadError
from .order import merge_in_dependency_order
from .utils import format_node_path

BASE_KEY = "$base"
"""A mapping, or a list of mappings, merged underneath the node."""


def merge_bases(config: DictConfig | ListConfig) -> None:
    """Merge every `$base` underneath its node in place, in dependency order.

    Args:
        config: The config to process.

    Raises:
        ConfigLoadError: If a `$base` is not a mapping or a list of mappings,
            cannot be resolved, or if `$base` references form a cycle.
    """  # noqa: DOC502
    merge_in_dependency_order(config, BASE_KEY, _merge_base)


def _merge_base(node: DictConfig, base: Any) -> None:
    if isinstance(base, ListConfig):
        bases = [base[index] for index in range(len(base))]
        if not all(isinstance(item, DictConfig) for item in bases):
            raise ConfigLoadError(
                f"List-valued `{BASE_KEY}` in `{format_node_path(node)}` must contain "
                "only mappings."
            )
    elif isinstance(base, DictConfig):
        bases = [base]
    else:
        raise ConfigLoadError(
            f"`{BASE_KEY}` in `{format_node_path(node)}` is not a mapping or a list of "
            "mappings."
        )
    node.pop(BASE_KEY)
    merged_config = cast(DictConfig, OmegaConf.merge(*bases, node))
    for key in list(merged_config.keys()):
        node[key] = merged_config._get_node(key)
