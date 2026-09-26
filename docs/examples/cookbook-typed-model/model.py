from dataclasses import dataclass
from typing import Literal

from omegaconf import MISSING

from omegakit import Configurable


class Encoder:
    pass


@dataclass
class ConvConfig:
    channels: int = 16
    kernel: Literal[3, 5] = 3


class ConvEncoder(Encoder, Configurable[ConvConfig]):
    def __init__(self, channels: int, kernel: int) -> None:
        self.channels = channels
        self.kernel = kernel


@dataclass
class MlpConfig:
    hidden: list[int] = MISSING


class MlpEncoder(Encoder, Configurable[MlpConfig]):
    def __init__(self, hidden: list[int]) -> None:
        self.hidden = hidden


@dataclass
class ModelConfig:
    encoder: Encoder
    dropout: float = 0.1


class Model(Configurable[ModelConfig]):
    def __init__(self, encoder: Encoder, dropout: float) -> None:
        self.encoder = encoder
        self.dropout = dropout
