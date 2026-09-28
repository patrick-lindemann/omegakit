from dataclasses import dataclass
from typing import Literal

from torch import nn


@dataclass
class Training:
    epochs: int
    schedule: Literal["constant", "cosine"] = "constant"


@dataclass
class Experiment:
    training: Training
    model: nn.Module
