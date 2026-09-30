from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Self, TypedDict, assert_type, override

from omegaconf import DictConfig

from omegakit import Configurable, instantiate, make_node
from tests.schemas import (
    A,
    Animal,
    B,
    Base,
    Dog,
    Encoder,
    Kind,
    Model,
    ModelConfig,
)

# Checked by pyright only; pytest does not collect this module. Each targeted ignore
# marks an error pyright must report: `reportUnnecessaryTypeIgnoreComment` fails the
# check if one of them stops firing.


class WrongModel(Configurable):
    """A `from_config` with a wrong argument type and a misspelled field."""

    schema = ModelConfig

    def __init__(self, kind: Base, depth: int, encoder: Encoder | None) -> None: ...

    @classmethod
    @override
    def from_config(cls, config: ModelConfig, **kwargs: Any) -> Self:
        assert_type(config.kind, Kind)
        assert_type(config.encoder, Encoder | None)
        kind = instantiate(make_node(A if config.kind is Kind.A else B), schema=Base)
        cls(config.kind, config.depth, config.encoder)  # pyright: ignore[reportArgumentType]
        return cls(kind, config.dpth, config.encoder)  # pyright: ignore[reportAttributeAccessIssue]


class SelfFactory(Animal):
    """A factory must annotate its base class; `Self` with a subclass is an error."""

    @classmethod
    @override
    def from_config(cls, config: Any, **kwargs: Any) -> Self:
        return Dog(0, 0)  # pyright: ignore[reportReturnType]


class WrongSchema(Configurable):
    """A schema must be a dataclass."""

    schema = Encoder  # pyright: ignore[reportAssignmentType]


def check_instantiate_types(config: DictConfig) -> None:
    assert_type(instantiate(config, schema=Model), Model)
    assert_type(instantiate(config, schema=Animal), Animal)
    assert_type(Model.from_config(ModelConfig(depth=1)), Model)


class CollectionConfig(TypedDict):
    sources: list[str]


@dataclass
class Collection[TRecord](Configurable):
    """Mirrors a TypedDict-typed `from_config` with an extra parameter."""

    records: list[TRecord]
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    @override
    def from_config(
        cls, config: CollectionConfig, file_path: Path | None = None, **kwargs: Any
    ) -> Self:
        assert_type(config["sources"], list[str])
        return cls(records=[])


def check_typed_dict_from_config() -> None:
    assert_type(
        Collection[int].from_config({"sources": []}, file_path=Path("x")),
        Collection[int],
    )
