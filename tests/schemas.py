from collections.abc import Callable
from dataclasses import InitVar, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Protocol, Self, override

from omegaconf import MISSING
from typing_extensions import TypeVar

from omegakit import Configurable, instantiate, node

ConfigT = TypeVar("ConfigT")


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
    """The schema of the design's worked example."""

    kind: Kind = Kind.A
    depth: int = MISSING
    encoder: Encoder | None = None


class Model(Configurable[ModelConfig]):
    """The design's worked example, with a custom `from_config`."""

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
        kind = instantiate(node(A if config.kind is Kind.A else B), Base)
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


class Mid(Configurable[ConfigT]):
    """A generic intermediate class without a type variable default."""

    def __init__(self, **fields: Any) -> None:
        self.fields = fields


DefaultT = TypeVar("DefaultT", default=EncoderConfig)


class MidWithDefault(Configurable[DefaultT]):
    """A generic intermediate class whose type variable defaults to a schema."""

    def __init__(self, **fields: Any) -> None:
        self.fields = fields


class Leaf(Mid[EncoderConfig]):
    """Parametrizes a generic intermediate class."""


class Mixin[T]:
    """A generic mixin that is not a `Configurable`."""


class MixedIn(Mixin[int], TypedEncoder):
    """Lists a generic mixin before its `Configurable` base."""


class Untyped(Configurable):
    """A bare `Configurable`, which has no schema."""

    def __init__(self, **fields: Any) -> None:
        self.fields = fields


@dataclass
class InitFalseConfig:
    value: int = 0
    derived: int = field(init=False, default=0)


class InitFalse(Configurable[InitFalseConfig]):
    def __init__(self, **fields: Any) -> None: ...


@dataclass
class InitVarConfig:
    value: int = 0
    seed: InitVar[int] = 0


class WithInitVar(Configurable[InitVarConfig]):
    def __init__(self, **fields: Any) -> None: ...


@dataclass(kw_only=True)
class KwOnlyConfig:
    value: int = 0


class KwOnly(Configurable[KwOnlyConfig]):
    def __init__(self, **fields: Any) -> None: ...


@dataclass
class TupleConfig:
    values: tuple[int, ...] = ()


class WithTuple(Configurable[TupleConfig]):
    def __init__(self, **fields: Any) -> None: ...


@dataclass
class SetConfig:
    values: set[int] = field(default_factory=set)


class WithSet(Configurable[SetConfig]):
    def __init__(self, **fields: Any) -> None: ...


@dataclass
class ObjectListConfig:
    encoders: list[Encoder] = field(default_factory=list)


class WithObjectList(Configurable[ObjectListConfig]):
    def __init__(self, **fields: Any) -> None: ...


@dataclass
class MixedUnionConfig:
    value: int | Encoder = 0


class WithMixedUnion(Configurable[MixedUnionConfig]):
    def __init__(self, **fields: Any) -> None: ...


@dataclass
class UnresolvableConfig:
    value: "Missing" = None  # type: ignore[name-defined]  # noqa: F821


class WithUnresolvable(Configurable[UnresolvableConfig]):
    def __init__(self, **fields: Any) -> None: ...


@dataclass
class PointConfig:
    x: int = 0
    y: int = 0


class MissingParameter(Configurable[PointConfig]):
    def __init__(self, x: int, y: int, z: int) -> None: ...


class ExtraField(Configurable[PointConfig]):
    def __init__(self, x: int) -> None: ...


class ExtraFieldWithKwargs(Configurable[PointConfig]):
    def __init__(self, x: int, **extra: Any) -> None: ...


class FloatParameters(Configurable[PointConfig]):
    def __init__(self, x: float, y: float) -> None: ...


class StrParameter(Configurable[PointConfig]):
    def __init__(self, x: str, y: int) -> None: ...


class CustomFromConfig(Configurable[PointConfig]):
    def __init__(self, z: int) -> None:
        self.z = z

    @classmethod
    @override
    def from_config(cls, config: PointConfig, **kwargs: Any) -> Self:
        return cls(config.x + config.y)


@dataclass
class OptionalEncoderConfig:
    encoder: Encoder | None = None


class NeedsEncoder(Configurable[OptionalEncoderConfig]):
    def __init__(self, encoder: Encoder) -> None: ...


@dataclass
class SubclassConfig:
    child: A | None = None


class TakesBase(Configurable[SubclassConfig]):
    def __init__(self, child: Base | None) -> None: ...


@dataclass
class GenericConfig:
    values: list[int] = field(default_factory=list)


class GenericParameter(Configurable[GenericConfig]):
    def __init__(self, values: list[str]) -> None: ...


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
    """A module-level factory function for `node`."""
    return Encoder(width)


@dataclass
class WrapperConfig:
    width: Any = 1


class Wrapper(Configurable[WrapperConfig]):
    """Builds a code-chosen `TypedEncoder` child with `node`."""

    def __init__(self, inner: TypedEncoder) -> None:
        self.inner = inner

    @classmethod
    @override
    def from_config(cls, config: WrapperConfig, **kwargs: Any) -> Self:
        return cls(instantiate(node(TypedEncoder, width=config.width), TypedEncoder))


@dataclass
class DataclassUnionConfig:
    value: Sub | int = 0


class WithDataclassUnion(Configurable[DataclassUnionConfig]):
    def __init__(self, **fields: Any) -> None: ...
