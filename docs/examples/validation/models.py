from dataclasses import dataclass

from omegakit import Configurable


@dataclass
class EncoderConfig:
    width: int
    layers: int = 2


class Encoder(Configurable[EncoderConfig]):
    def __init__(self, width: int, layers: int) -> None:
        self.width = width
        self.layers = layers
