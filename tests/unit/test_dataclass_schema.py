import functools
from dataclasses import dataclass, field
from typing import Any

import pytest

from omegakit import ConfigValidationError, instantiate, prepare, validate
from tests.schemas import Base, Encoder


@dataclass
class Optimizer:
    lr: float
    epochs: int = 1


@dataclass
class Momentum(Optimizer):
    momentum: float = 0.9


@dataclass
class Schedule:
    warmup: int = 0


@dataclass
class Run:
    encoder: Encoder
    optimizer: Any = None
    schedule: Schedule = field(default_factory=Schedule)


@dataclass
class Child(Base):
    size: int = 1


@dataclass
class Holder:
    child: Base


OPTIMIZER = f"{__name__}.Optimizer"
MOMENTUM = f"{__name__}.Momentum"
RUN = f"{__name__}.Run"


def test_dataclass_class_node_is_validated():
    config = {"$class": OPTIMIZER, "lr": 1, "epochs": "many"}
    with pytest.raises(ConfigValidationError, match=r"`epochs` \(Optimizer\)"):
        validate(config)
    with pytest.raises(ConfigValidationError, match=r"`epochs` \(Optimizer\)"):
        validate(config, schema=Optimizer)


def test_dataclass_class_node_is_built_with_converted_values():
    optimizer = instantiate({"$class": OPTIMIZER, "lr": 1, "epochs": "4"})
    assert optimizer == Optimizer(lr=1.0, epochs=4)
    assert type(optimizer.lr) is float
    assert type(optimizer.epochs) is int


def test_dataclass_class_node_rejects_unknown_key():
    with pytest.raises(ConfigValidationError, match="Unknown field"):
        instantiate({"$class": OPTIMIZER, "lr": 1, "beta": 2})


def test_dataclass_class_node_rejects_missing_required_field():
    with pytest.raises(ConfigValidationError, match="lr"):
        instantiate({"$class": OPTIMIZER})


def test_dataclass_class_node_builds_object_fields_and_sections():
    run = instantiate(
        {
            "$class": RUN,
            "encoder": {"$class": "tests.schemas.Encoder", "width": 3},
            "optimizer": {"$class": OPTIMIZER, "lr": "0.5"},
            "schedule": {"warmup": "10"},
        }
    )
    assert run.encoder.width == 3
    assert run.optimizer == Optimizer(lr=0.5)
    assert run.schedule == Schedule(warmup=10)


def test_dataclass_class_node_nested_in_plain_mapping_is_validated():
    with pytest.raises(ConfigValidationError, match=r"`optimizers\.0\.epochs`"):
        validate({"optimizers": [{"$class": OPTIMIZER, "lr": 1, "epochs": "x"}]})


def test_dataclass_class_node_as_partial():
    make = instantiate({"$class": OPTIMIZER, "epochs": "2", "lr": 1, "$partial": True})
    assert isinstance(make, functools.partial)
    assert make() == Optimizer(lr=1.0, epochs=2)
    assert make(epochs=5) == Optimizer(lr=1.0, epochs=5)


def test_prepare_dataclass_class_node():
    make = prepare({"$class": OPTIMIZER, "lr": "0.1"})
    assert make(epochs=3) == Optimizer(lr=0.1, epochs=3)


def test_dataclass_subclass_is_checked_against_its_own_fields():
    with pytest.raises(ConfigValidationError, match=r"`momentum` \(Momentum\)"):
        validate({"$class": MOMENTUM, "lr": 1, "momentum": "high"}, schema=Optimizer)
    momentum = instantiate({"$class": MOMENTUM, "lr": 1, "momentum": "0.5"})
    assert momentum == Momentum(lr=1.0, momentum=0.5)


def test_dataclass_subclass_of_plain_class_fills_object_field():
    holder = instantiate(
        {"$class": f"{__name__}.Holder", "child": {"$class": f"{__name__}.Child"}}
    )
    assert holder.child == Child(size=1)
    with pytest.raises(ConfigValidationError, match=r"`child.size` \(Child\)"):
        validate(
            {
                "$class": f"{__name__}.Holder",
                "child": {"$class": f"{__name__}.Child", "size": "big"},
            }
        )
