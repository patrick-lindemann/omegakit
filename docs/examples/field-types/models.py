from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

from omegakit import Configurable


class Activation(Enum):
    RELU = "relu"
    GELU = "gelu"


@dataclass
class Schedule:
    warmup: int = 0
    decay: float = 0.1


class Layer:
    def __init__(self, width: int) -> None:
        self.width = width


@dataclass
class ModelConfig:
    activation: Activation = Activation.RELU
    mode: Literal["train", "eval"] = "train"
    kernel: tuple[int, int] = (3, 3)
    schedule: Schedule | float = 0.0
    layers: list[Layer] = field(default_factory=list)
    steps: int = field(init=False, default=0)


class Model(Configurable[ModelConfig]):
    def __init__(
        self,
        activation: Activation,
        mode: str,
        kernel: tuple[int, int],
        schedule: Schedule | float,
        layers: list[Layer],
    ) -> None:
        self.activation = activation
        self.mode = mode
        self.kernel = kernel
        self.schedule = schedule
        self.layers = layers
