import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Self, override

from omegaconf import MISSING

from omegakit import Configurable, instantiate, load_config, make_node


class Kind(Enum):
    A = "alpha"
    B = "beta"


class Base:
    pass


class A(Base):
    pass


class B(Base):
    pass


class Encoder:
    def __init__(self, width: int) -> None:
        self.width = width


@dataclass
class ModelConfig:
    kind: Kind = Kind.A
    depth: int = MISSING
    encoder: Encoder | None = None


class Model(Configurable[ModelConfig]):
    def __init__(self, kind: Base, depth: int, encoder: Encoder | None) -> None:
        self.kind = kind
        self.depth = depth
        self.encoder = encoder

    @classmethod
    @override
    def from_config(cls, config: ModelConfig, **kwargs: Any) -> Self:
        kind = instantiate(make_node(A if config.kind is Kind.A else B), Base)
        return cls(kind, config.depth, config.encoder, **kwargs)


YAML = """
model:
  $class: __main__.Model
  kind: B
  depth: 3
  encoder:
    $class: __main__.Encoder
    width: ${model.depth}
"""

with tempfile.TemporaryDirectory() as directory:
    path = Path(directory, "app.yaml")
    path.write_text(YAML)
    cfg = load_config(path, overrides=["model.kind=A"])
    model = instantiate(cfg.model, Model)

assert isinstance(model.kind, A)
assert model.depth == 3
assert model.encoder is not None and model.encoder.width == 3
