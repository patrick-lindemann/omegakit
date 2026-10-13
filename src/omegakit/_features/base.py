from omegaconf import DictConfig, ListConfig, TupleConfig

from omegakit._core.error import OmegaKitBaseException
from omegakit._core.utils.copy import copy_with_root
from omegakit._core.utils.describe import describe_node
from omegakit._core.utils.merge import merge_under, walk_mergeable

BASE_KEY = "$base"


class ConfigInheritanceError(OmegaKitBaseException):
    pass


class BaseTypeError(ConfigInheritanceError, TypeError):
    pass


def merge_bases[TConfig: DictConfig | ListConfig | TupleConfig](
    config: TConfig, copy: bool = True
) -> TConfig:
    if copy:
        config = copy_with_root(config)
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
    return config
