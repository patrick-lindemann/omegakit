from dataclasses import dataclass
from typing import Literal

from torch import nn

from omegakit import Configurable


@dataclass
class MLPConfig:
    hidden: int
    activation: Literal["relu", "tanh"] = "tanh"


class MLP(nn.Sequential, Configurable[MLPConfig]):
    """A multilayer perceptron from one input to one output."""

    def __init__(self, hidden: int, activation: Literal["relu", "tanh"] = "tanh"):
        super().__init__(
            nn.Linear(1, hidden),
            nn.Tanh() if activation == "tanh" else nn.ReLU(),
            nn.Linear(hidden, 1),
        )
