from omegaconf import DictConfig, ListConfig, TupleConfig

from omegakit._core.errors import ConfigMergeError
from omegakit._core.utils.copy import copy_with_root
from omegakit._core.utils.describe import get_full_key
from omegakit._core.utils.merge import merge_under, walk_mergeable

EACH_KEY = "$each"


def apply_each[TConfig: DictConfig | ListConfig | TupleConfig](
    config: TConfig, copy: bool = True
) -> TConfig:
    if copy:
        config = copy_with_root(config)
    for node, each in walk_mergeable(config, EACH_KEY):
        if not isinstance(each, DictConfig):
            raise ConfigMergeError(
                f"`{EACH_KEY}` must be a mapping, not `{each!r}`.", get_full_key(node)
            )
        del node[EACH_KEY]
        for key in list(node.keys()):
            child = node._get_node(key)
            # Only a child that holds a mapping, not `null`, `???` or `${...}`
            if (
                isinstance(child, DictConfig)
                and isinstance(child._value(), dict)
                and not str(key).startswith("$")
            ):
                merge_under(child, each)
    return config
