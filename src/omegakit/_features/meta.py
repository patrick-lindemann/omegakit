from omegaconf import DictConfig, ListConfig, TupleConfig

from omegakit._utils.copy import copy_with_root
from omegakit._utils.walk import walk

META_KEY = "$meta"


def remove_meta[TConfig: DictConfig | ListConfig | TupleConfig](
    config: TConfig, copy: bool = True
) -> TConfig:
    if copy:
        config = copy_with_root(config)
    for node in walk(config):
        # `META_KEY in node` is false for a `$meta` that cannot be read, such as `???`
        if isinstance(node, DictConfig) and META_KEY in node.keys():  # noqa: SIM118
            del node[META_KEY]
    return config
