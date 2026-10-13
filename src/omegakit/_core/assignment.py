from dataclasses import dataclass
from typing import Any

from omegaconf import DictConfig, ListConfig


@dataclass(frozen=True)
class Assignment:
    parent: DictConfig | ListConfig
    key: Any
    value: Any
