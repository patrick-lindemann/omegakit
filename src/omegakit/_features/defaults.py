from omegaconf import DictConfig, ListConfig, TupleConfig

from omegakit._core.error import OmegaKitBaseException
from omegakit._core.merge import copy_with_root, merge_under, walk_mergeable
from omegakit._utils.describe import describe_node

DEFAULTS_KEY = "$defaults"


class ConfigDefaultsError(OmegaKitBaseException):
    pass


class DefaultsTypeError(ConfigDefaultsError, TypeError):
    pass


def apply_defaults[ConfigT: DictConfig | ListConfig | TupleConfig](
    config: ConfigT, copy: bool = True
) -> ConfigT:
    if copy:
        config = copy_with_root(config)
    for node, defaults in walk_mergeable(config, DEFAULTS_KEY):
        if not isinstance(defaults, DictConfig):
            error = DefaultsTypeError(
                f"`{DEFAULTS_KEY}` must be a mapping, not `{defaults!r}`."
            )
            error.add_note(f"  at {describe_node(node)}")
            raise error
        del node[DEFAULTS_KEY]
        for key in list(node.keys()):
            child = node._get_node(key)
            # Only a child that holds a mapping, not `null`, `???` or `${...}`
            if (
                isinstance(child, DictConfig)
                and isinstance(child._value(), dict)
                and not str(key).startswith("$")
            ):
                merge_under(child, defaults)
    return config
