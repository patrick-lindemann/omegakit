from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Self, override  # noqa: TID251

import pytest

from omegakit import Configurable, ConfigValidationError, check_schema, instantiate
from tests import schemas
from tests.schemas import A, Base, Encoder, PointConfig

if TYPE_CHECKING:
    from decimal import Decimal

# Contracts: §10 Typed configs (consistency check).


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


def test_check_schema_accepts_matching_class():
    check_schema(schemas.TypedEncoder)


def test_check_schema_required_parameter_needs_a_field():
    with pytest.raises(ConfigValidationError, match="required parameter `z`"):
        check_schema(schemas.MissingParameter)


def test_check_schema_extra_field_needs_kwargs():
    with pytest.raises(ConfigValidationError, match="Field `y`"):
        check_schema(ExtraField)
    check_schema(ExtraFieldWithKwargs)


@dataclass
class PositionalConfig:
    x: int


class PositionalBehindKwargs(Configurable[PositionalConfig]):
    def __init__(self, x: int, /, **kwargs: Any) -> None:
        self.x = x


def test_check_schema_rejects_positional_only_parameters_behind_kwargs():
    with pytest.raises(ConfigValidationError, match="Field `x`"):
        check_schema(PositionalBehindKwargs)


@dataclass
class PartlyResolvableConfig:
    x: str
    amount: int = 0


class PartlyResolvable(Configurable[PartlyResolvableConfig]):
    def __init__(self, x: int, amount: "Decimal | int" = 0) -> None: ...


class Unresolvable(Configurable[PartlyResolvableConfig]):
    def __init__(self, x: str, amount: "Decimal | int" = 0) -> None: ...


def test_check_schema_checks_annotations_that_resolve_when_others_do_not():
    with pytest.raises(ConfigValidationError, match="Field `x`"):
        check_schema(PartlyResolvable)
    check_schema(Unresolvable)


def test_check_schema_int_field_is_assignable_to_float():
    check_schema(FloatParameters)


def test_check_schema_rejects_unassignable_annotation():
    with pytest.raises(ConfigValidationError, match="not assignable"):
        check_schema(StrParameter)


def test_check_schema_subclass_field_is_assignable_to_base():
    check_schema(TakesBase)


def test_check_schema_optional_field_is_not_assignable_to_required():
    with pytest.raises(ConfigValidationError, match="not assignable"):
        check_schema(NeedsEncoder)


def test_check_schema_skips_generic_annotations():
    check_schema(GenericParameter)


def test_check_schema_skips_custom_from_config():
    check_schema(CustomFromConfig)
    assert instantiate({"$class": f"{__name__}.CustomFromConfig", "x": 1}).z == 1


def test_check_schema_ignores_classes_without_schema():
    check_schema(schemas.Untyped)
    check_schema(schemas.Encoder)


def test_check_schema_runs_before_children_are_built():
    with pytest.raises(ConfigValidationError, match="required parameter `z`"):
        instantiate(
            {
                "$class": "tests.schemas.MissingParameter",
                "x": {"$class": "tests.helpers.Failing"},
            }
        )
