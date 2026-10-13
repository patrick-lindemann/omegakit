from omegaconf import DictConfig, ListConfig, TupleConfig

from omegakit._core.walk import walk

META_KEY = "$meta"


def remove_meta(config: DictConfig | ListConfig | TupleConfig) -> None:
    for node in walk(config):
        # `META_KEY in node` is false for a `$meta` that cannot be read, such as `???`
        if isinstance(node, DictConfig) and META_KEY in node.keys():  # noqa: SIM118
            del node[META_KEY]
