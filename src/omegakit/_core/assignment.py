from typing import Any, NamedTuple

from omegaconf import DictConfig, ListConfig


class Assignment(NamedTuple):
    parent: DictConfig | ListConfig
    key: Any
    value: Any
