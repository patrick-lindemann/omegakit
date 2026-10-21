import dataclasses
import enum
import pathlib
import typing
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal, TypedDict

import typing_extensions
from typing_extensions import NotRequired, override

from omegakit._core.configurable import Configurable

CALLS = []
SETTINGS = {"seed": 0}
BACKBONE = {"depth": "3"}
BACKBONES = [{"depth": "3"}]
NAMED_BACKBONES = {"small": {"depth": "3"}}
BACKBONE_PAIR = ({"depth": "3"}, {"depth": 4})
WRONG_BACKBONES = [{"depth": 3, "width": 2}]
NAMED_WRONG_BACKBONES = {"small": {"depth": 3, "width": 2}}
WRONG_BACKBONE_PAIR = ({"depth": 3}, {"depth": "deep"})
NUMBERS = [1, 2]
RAW_NODES = [{"$target": "tests.targets.nowhere"}]


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


@dataclass
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


@dataclass
class FastOptimizer(Optimizer):
    pass


@dataclass
class Scaled:
    n: int
    scale: dataclasses.InitVar[int]
    noise: float = 0.1

    def __post_init__(self, scale):
        self.n *= scale


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


@dataclass
class Layer(Configurable):
    width: int
    bias: bool = True


@dataclass
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


def _make_collection_config(typed_dict: Any) -> Any:
    select_config = typed_dict("SelectFilterConfig", {"select": list[str]})
    match_config = typed_dict("MatchFilterConfig", {"match": str})
    file_config = typed_dict(
        "FileSourceConfig",
        {
            "type": Literal["file"],
            "path": str,
            "filter": NotRequired[select_config | match_config],
        },
    )
    directory_config = typed_dict(
        "DirectorySourceConfig",
        {"type": Literal["directory"], "path": str, "depth": NotRequired[int]},
    )
    url_config = typed_dict(
        "UrlSourceConfig", {"url": str, "retries": NotRequired[int]}
    )
    return typed_dict(
        "CollectionConfig",
        {"sources": list[file_config | directory_config | url_config]},
    )


CollectionConfig = _make_collection_config(typing.TypedDict)
BackportedCollectionConfig = _make_collection_config(typing_extensions.TypedDict)
URL_SOURCE = {"url": "https://example.com", "retries": "2"}


class Collection(Model):
    schema = CollectionConfig


class BackportedCollection(Model):
    schema = BackportedCollectionConfig


def make_item(**kwargs):
    return Item(**kwargs)


def make_item_class():
    return SmallItem


def make_number_class():
    return int


@dataclass
class ItemMaker:
    kind: type[Item]


ITEM = Item()
CALLS.clear()
