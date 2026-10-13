from omegaconf import DictConfig, ListConfig, TupleConfig

from omegakit._core.error import OmegaKitBaseException
from omegakit._utils.copy import copy_with_root
from omegakit._utils.describe import describe_node
from omegakit._utils.merge import merge_under, walk_mergeable

EACH_KEY = "$each"


class ConfigEachError(OmegaKitBaseException):
    pass


class EachTypeError(ConfigEachError, TypeError):
    pass


def apply_each[TConfig: DictConfig | ListConfig | TupleConfig](
    config: TConfig, copy: bool = True
) -> TConfig:
    if copy:
        config = copy_with_root(config)
    for node, each in walk_mergeable(config, EACH_KEY):
        if not isinstance(each, DictConfig):
            error = EachTypeError(f"`{EACH_KEY}` must be a mapping, not `{each!r}`.")
            error.add_note(f"  at {describe_node(node)}")
            raise error
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
