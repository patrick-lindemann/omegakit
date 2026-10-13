import sys
from pathlib import Path
from types import ModuleType

import pytest

_TARGETS = """
import dataclasses
import enum
import pathlib
from collections.abc import Callable
from typing import Any, Literal, NotRequired, TypedDict, override

from omegakit.configurable import Configurable

CALLS = []
SETTINGS = {"seed": 0}


class Item:
    def __init__(self, **kwargs):
        CALLS.append(kwargs.get("name"))
        self.kwargs = kwargs


class Configured:
    def __init__(self, config, kwargs):
        self.config = config
        self.kwargs = kwargs

    @classmethod
    def from_config(cls, config, **kwargs):
        return cls(config, kwargs)


class _Factory:
    def from_config(self, config, **kwargs):
        return Configured(config, kwargs)


FACTORY = _Factory()


def fail(**kwargs):
    raise UnicodeDecodeError("utf-8", b"", 0, 1, "broken")


class SmallItem(Item):
    pass


class Mode(enum.Enum):
    FAST = "fast"
    SLOW = "slow"


@dataclasses.dataclass
class Optimizer:
    lr: float
    steps: int = 10
    mode: Mode = Mode.FAST
    betas: tuple[float, float] = (0.9, 0.99)
    log_dir: pathlib.Path = pathlib.Path("logs")
    total: float = dataclasses.field(init=False, default=0.0)

    def __post_init__(self):
        CALLS.append("optimizer")
        self.total = self.lr * self.steps


@dataclasses.dataclass
class FastOptimizer(Optimizer):
    pass


class ModelConfig(TypedDict):
    depth: int
    activation: NotRequired[Literal["relu", "tanh"]]
    encoder: NotRequired[Item | None]


class Model(Configurable):
    schema = ModelConfig

    def __init__(self, config, kwargs):
        self.config = config
        self.kwargs = kwargs

    @classmethod
    @override
    def from_config(cls, config, **kwargs):
        return cls(config, kwargs)


@dataclasses.dataclass
class Layer(Configurable):
    width: int
    bias: bool = True


@dataclasses.dataclass
class Experiment:
    model: Model
    optimizer: Optimizer = dataclasses.field(default_factory=lambda: Optimizer(0.1))
    seed: int = 0
    items: list[Item] = dataclasses.field(default_factory=list)
    named_items: dict[str, Item] = dataclasses.field(default_factory=dict)
    stages: list[Optimizer] = dataclasses.field(default_factory=list)
    schedules: dict[str, Optimizer] = dataclasses.field(default_factory=dict)
    schedule: Callable[..., Any] | None = None
    extra: Any = None
    backbone: ModelConfig | None = None
    pair: tuple[Item, float] | None = None
    phases: tuple[ModelConfig, ...] = ()


class BrokenModel(Model):
    schema = dict


def make_item(**kwargs):
    return Item(**kwargs)


ITEM = Item()
CALLS.clear()
"""


@pytest.fixture
def targets(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    (tmp_path / "config_targets.py").write_text(_TARGETS)
    monkeypatch.syspath_prepend(tmp_path)
    monkeypatch.delitem(sys.modules, "config_targets", raising=False)
    import config_targets  # pyright: ignore[reportMissingImports]

    return config_targets
