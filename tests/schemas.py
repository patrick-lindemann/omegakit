from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Literal, Protocol, Self, TypedDict, override

from omegaconf import MISSING

from omegakit import Configurable


class Kind(Enum):
    """Choices given by member name in YAML."""

    A = "alpha"
    B = "beta"


class Base:
    """A base class for code-chosen children."""


class A(Base):
    """The child chosen for `Kind.A`."""


class B(Base):
    """The child chosen for `Kind.B`."""


class Encoder:
    """A plain class used as an object field."""

    def __init__(self, width: int = 1) -> None:
        self.width = width


class Decoder:
    """A plain class of the wrong type for `Encoder` fields."""


type EncoderAlias = Encoder


class Greeter(Protocol):
    """A protocol that is not runtime-checkable."""

    def greet(self) -> str: ...


@dataclass
class Sub:
    """A native nested dataclass whose `__post_init__` must run."""

    value: int = 0
    doubled: int = 0

    def __post_init__(self) -> None:
        self.doubled = self.value * 2


@dataclass
class EncoderConfig:
    """The schema of `TypedEncoder`."""

    width: int = 1


class TypedEncoder(Configurable[EncoderConfig]):
    """A `Configurable` built through the default `from_config`."""

    def __init__(self, width: int) -> None:
        self.width = width


@dataclass
class ModelConfig:
    """The schema of `Model`: an enum, a required value and an optional object."""

    kind: Kind = Kind.A
    depth: int = MISSING
    encoder: Encoder | None = None


class Model(Configurable[ModelConfig]):
    """A class whose `from_config` picks a child by enum and passes extra arguments."""

    def __init__(
        self, kind: Base, depth: int, encoder: Encoder | None, **extra: Any
    ) -> None:
        self.kind = kind
        self.depth = depth
        self.encoder = encoder
        self.extra = extra

    @classmethod
    @override
    def from_config(cls, config: ModelConfig, **kwargs: Any) -> Self:
        kind = A() if config.kind is Kind.A else B()
        return cls(kind, config.depth, config.encoder, **kwargs)


@dataclass
class FieldsConfig:
    """A schema with every kind of field."""

    sub: Sub = field(default_factory=Sub)
    subs: list[Sub] = field(default_factory=list)
    by_name: dict[str, Sub] = field(default_factory=dict)
    path: Path = Path(".")
    kind: Kind = Kind.A
    number: int | str = 0
    count: int = 0
    anything: Any = None
    encoder: Encoder | None = None
    aliased: EncoderAlias | None = None
    greeter: Greeter | None = None
    factory: Callable[..., Encoder] | None = None


class Fields(Configurable[FieldsConfig]):
    """Stores the typed config it receives."""

    def __init__(self, **fields: Any) -> None:
        self.fields = fields


@dataclass
class RequiredObjectConfig:
    """A schema with a required object field."""

    encoder: Encoder


class RequiredObject(Configurable[RequiredObjectConfig]):
    """Requires an `Encoder`."""

    def __init__(self, encoder: Encoder) -> None:
        self.encoder = encoder


class Untyped(Configurable):
    """A bare `Configurable`, which has no schema."""

    def __init__(self, **fields: Any) -> None:
        self.fields = fields


@dataclass
class InitFalseConfig:
    value: int = 0
    derived: int = field(init=False, default=0)


class InitFalse(Configurable[InitFalseConfig]):
    def __init__(self, **fields: Any) -> None:
        self.fields = fields


@dataclass
class PointConfig:
    x: int = 0
    y: int = 0


class MissingParameter(Configurable[PointConfig]):
    def __init__(self, x: int, y: int, z: int) -> None: ...


class Animal(Configurable[PointConfig]):
    """A factory base whose `from_config` returns a subclass."""

    def __init__(self, x: int, y: int) -> None:
        self.x = x
        self.y = y

    @classmethod
    @override
    def from_config(cls, config: PointConfig, **kwargs: Any) -> "Animal":
        return Dog(config.x, config.y) if config.x > 0 else Cat(config.x, config.y)


class Dog(Animal):
    """Built by `Animal.from_config` for positive `x`."""


class Cat(Animal):
    """Built by `Animal.from_config` otherwise."""


def make_encoder(width: int) -> Encoder:
    """A module-level factory function for `make_node`."""
    return Encoder(width)


@dataclass
class DataConfig:
    """A plain-value section of the root schema."""

    root: Path = Path("data")
    batch_size: int = 32


@dataclass
class TrainingConfig:
    """A root schema section holding a child object."""

    model: Model
    epochs: int = 1


@dataclass
class AppConfig:
    """A root schema with a section that holds an object field."""

    training: TrainingConfig
    seed: int = 0
    data: DataConfig = field(default_factory=DataConfig)
    callbacks: Any = None


@dataclass
class ModeSection:
    """A nested section with a literal field."""

    mode: Literal["fast", "slow"] = "fast"


@dataclass
class LiteralConfig:
    """A schema with literal fields in every supported position."""

    mode: Literal["train", "eval"] = "train"
    level: Literal[1, 2, 3] = 1
    batch: int | Literal["auto"] = "auto"
    maybe: Literal["a", "b"] | None = None
    modes: list[Literal["x", "y"]] = field(default_factory=list)
    section: ModeSection = field(default_factory=ModeSection)
    sections: list[ModeSection] = field(default_factory=list)


@dataclass
class SectionWithObject:
    """A dataclass section that holds an object field."""

    encoder: Encoder
    size: int = 1


class Color(Enum):
    """An enum with string values."""

    RED = "red"
    BLUE = "blue"


class Clash(Enum):
    """An enum where a value equals another member's name."""

    A = "B"
    B = "x"


class Level(Enum):
    """An enum with integer values."""

    LOW = 1
    HIGH = 2


class PointDict(TypedDict):
    x: int


@dataclass
class TypesConfig:
    """A schema with the annotations beyond plain values and dataclasses."""

    pair: tuple[int, str] = (0, "a")
    numbers: tuple[int, ...] = ()
    sequence: Sequence[int] = field(default_factory=list)
    mapping: Mapping[str, int] = field(default_factory=dict)
    point: PointDict = field(default_factory=lambda: PointDict(x=0))
    color: Color = Color.RED
    clash: Clash = Clash.A
    level: Level = Level.LOW
    colors: dict[Color, int] = field(default_factory=dict)
    sub_or_int: Sub | int = 0
    sub_default: Sub | int = field(default_factory=Sub)
    list_or_int: list[int] | int = 0
    maybe_sub: Sub | None = None


class Types(Configurable[TypesConfig]):
    def __init__(self, **fields: Any) -> None:
        self.fields = fields


@dataclass
class ObjectContainersConfig:
    """A schema with lists and dicts of objects."""

    encoders: list[Encoder] = field(default_factory=list)
    by_name: dict[str, Encoder] = field(default_factory=dict)
    sections: list[SectionWithObject] = field(default_factory=list)
    maybe: list[Encoder] | None = None


class ObjectContainers(Configurable[ObjectContainersConfig]):
    def __init__(self, **fields: Any) -> None:
        self.fields = fields
