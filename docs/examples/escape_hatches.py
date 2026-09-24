from dataclasses import dataclass
from typing import Any, Self, TypedDict, override

from omegaconf import OmegaConf

from omegakit import Configurable, instantiate, prepare


class LegacyConfig(TypedDict):
    name: str


class Legacy(Configurable[LegacyConfig]):
    def __init__(self, name: str) -> None:
        self.name = name

    @classmethod
    @override
    def from_config(cls, config: LegacyConfig, **kwargs: Any) -> Self:
        return cls(config["name"].upper())


@dataclass
class OptimizerConfig:
    lr: float = 0.1
    extras: Any = None


class Optimizer(Configurable[OptimizerConfig]):
    def __init__(self, lr: float, extras: Any, params: list[float]) -> None:
        self.lr = lr
        self.extras = extras
        self.params = params

    @classmethod
    @override
    def from_config(cls, config: OptimizerConfig, **kwargs: Any) -> Self:
        return cls(config.lr, config.extras, **kwargs)


assert instantiate({"$class": "__main__.Legacy", "name": "x"}, Legacy).name == "X"

OmegaConf.register_new_resolver("marker", lambda: object())
config = OmegaConf.create({"$class": "__main__.Optimizer", "extras": "${marker:}"})
make_optimizer = prepare(config, Optimizer)
optimizer = make_optimizer(params=[1.0, 2.0])
assert optimizer.params == [1.0, 2.0]
assert type(optimizer.extras) is object
