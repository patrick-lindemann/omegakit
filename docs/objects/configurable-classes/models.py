from typing import Literal, TypedDict

from torch import nn
from typing_extensions import NotRequired

from omegakit import Configurable


class MLPConfig(TypedDict):
    hidden: int
    layers: NotRequired[int]
    activation: NotRequired[Literal["relu", "tanh"]]


class MLP(nn.Sequential, Configurable, schema=MLPConfig):
    """A multilayer perceptron from one input to one output."""

    def __init__(
        self,
        hidden: int,
        layers: int = 1,
        activation: Literal["relu", "tanh"] = "tanh",
    ) -> None:
        activation_class = nn.Tanh if activation == "tanh" else nn.ReLU
        modules: list[nn.Module] = [nn.Linear(1, hidden), activation_class()]
        for _ in range(layers - 1):
            modules += [nn.Linear(hidden, hidden), activation_class()]
        super().__init__(*modules, nn.Linear(hidden, 1))
