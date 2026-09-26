from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Literal

from omegaconf import MISSING

from omegakit import Configurable, instantiate, load_config, validate


class Kind(Enum):
    A = "alpha"
    B = "beta"


@dataclass
class EncoderConfig:
    width: int = 1


class Encoder(Configurable[EncoderConfig]):
    def __init__(self, width: int) -> None:
        self.width = width


@dataclass
class ModelConfig:
    kind: Kind = Kind.A
    depth: int = MISSING
    encoder: Encoder | None = None


class Model(Configurable[ModelConfig]):
    def __init__(self, kind: Kind, depth: int, encoder: Encoder | None) -> None:
        self.kind = kind
        self.depth = depth
        self.encoder = encoder


@dataclass
class DataConfig:
    root: Path = Path("data")
    split: Literal["train", "test"] = "train"
    batch_size: int = 32


@dataclass
class TrainingConfig:
    model: Model
    epochs: int = 1


@dataclass
class AppConfig:
    training: TrainingConfig
    seed: int = 0
    data: DataConfig = field(default_factory=DataConfig)


if __name__ == "__main__":
    # The YAML names `editor_app.Model`; running this file defines `__main__.Model`.
    import editor_app

    cfg = load_config(Path(__file__).parent / "editor" / "app.yaml")
    validate(cfg, schema=editor_app.AppConfig)
    model = instantiate(cfg.training.model, editor_app.Model)
    assert cfg.data.batch_size == 64
    assert model.depth == 7
    assert model.kind.name == "B"
    assert model.encoder is not None
    assert model.encoder.width == 8
