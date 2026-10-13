from omegaconf import DictConfig, ListConfig, TupleConfig

from omegakit._core.copy import copy_with_root
from omegakit._core.walk import walk

META_KEY = "$meta"


def remove_meta[ConfigT: DictConfig | ListConfig | TupleConfig](
    config: ConfigT, copy: bool = True
) -> ConfigT:
    if copy:
        config = copy_with_root(config)
    for node in walk(config):
        # `META_KEY in node` is false for a `$meta` that cannot be read, such as `???`
        if isinstance(node, DictConfig) and META_KEY in node.keys():  # noqa: SIM118
            del node[META_KEY]
    return config
