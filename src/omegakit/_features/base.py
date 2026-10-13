from omegaconf import DictConfig, ListConfig, TupleConfig

from omegakit._core.error import OmegaKitBaseException
from omegakit._core.merge import copy_with_root, merge_under, walk_mergeable
from omegakit._utils.describe import describe_node

BASE_KEY = "$base"


class ConfigInheritanceError(OmegaKitBaseException):
    pass


class BaseTypeError(ConfigInheritanceError, TypeError):
    pass


def merge_bases(config: DictConfig | ListConfig | TupleConfig) -> None:
    # Merged in a copy first, so that a failure leaves `config` unchanged
    config_copy = copy_with_root(config)
    _merge_bases(config_copy)
    _merge_bases(config)


def _merge_bases(config: DictConfig | ListConfig | TupleConfig) -> None:
    for node, base in walk_mergeable(config, BASE_KEY):
        bases = list(base) if isinstance(base, ListConfig) else [base]
        if not all(isinstance(item, DictConfig) for item in bases):
            error = BaseTypeError(
                f"`{BASE_KEY}` must be a mapping or a list of mappings, not `{base!r}`."
            )
            error.add_note(f"  at {describe_node(node)}")
            raise error
        del node[BASE_KEY]
        merge_under(node, *bases)
