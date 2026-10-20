import copy
from typing import TypeVar, cast

from omegaconf import DictConfig, ListConfig, TupleConfig

from .walk import walk

_TConfig = TypeVar("_TConfig", bound=DictConfig | ListConfig | TupleConfig)


def copy_with_root(config: _TConfig) -> _TConfig:
    # A copy of `config` alone would still resolve its interpolations in the
    # original root
    root = config._get_root()
    root_copy = copy.deepcopy(root)
    index = [node is config for node in walk(root)].index(True)
    return cast(_TConfig, list(walk(root_copy))[index])
