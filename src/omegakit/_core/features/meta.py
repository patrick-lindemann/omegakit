from typing import TypeVar

from omegaconf import DictConfig, ListConfig, TupleConfig

from omegakit._core.utils.copy import copy_with_root
from omegakit._core.utils.walk import walk

META_KEY = "$meta"
"""The key of data about a node, which `load_config` removes."""

_TConfig = TypeVar("_TConfig", bound=DictConfig | ListConfig | TupleConfig)


def remove_meta(config: _TConfig, copy: bool = True) -> _TConfig:
    """Remove every `$meta` from a config.

    Args:
        config: The config to transform.
        copy: Whether to leave `config` unchanged. Defaults to `True`.

    Returns:
        The config without `$meta` keys.
    """
    if copy:
        config = copy_with_root(config)
    for node in walk(config):
        # `META_KEY in node` is false for a `$meta` that cannot be read, such as `???`
        if isinstance(node, DictConfig) and META_KEY in node.keys():  # noqa: SIM118
            del node[META_KEY]
    return config
