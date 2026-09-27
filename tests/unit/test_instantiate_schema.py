import functools
from dataclasses import dataclass

import pytest

from omegakit import ConfigValidationError, instantiate, prepare
from tests.helpers import POINT, Point
from tests.schemas import Encoder, TypedEncoder


@dataclass
class Experiment:
    encoder: Encoder
    seed: int = 0
    name: str = "run"


@dataclass
class LongExperiment(Experiment):
    epochs: int = 10


class Failing(TypedEncoder):
    def __init__(self, width: int) -> None:
        raise ValueError("bad width")


ENCODER = {"$class": "tests.schemas.Encoder", "width": 3}


def test_root_without_class_builds_dataclass_schema():
    experiment = instantiate({"encoder": ENCODER, "seed": "7"}, schema=Experiment)
    assert type(experiment) is Experiment
    assert experiment.seed == 7
    assert experiment.encoder.width == 3


def test_root_without_class_builds_configurable_through_from_config():
    encoder = instantiate({"width": "4"}, schema=TypedEncoder)
    assert type(encoder) is TypedEncoder
    assert encoder.width == 4


def test_root_with_class_builds_subclass_of_schema():
    experiment = instantiate(
        {"$class": f"{__name__}.LongExperiment", "encoder": ENCODER, "epochs": "5"},
        schema=Experiment,
    )
    assert type(experiment) is LongExperiment
    assert experiment.epochs == 5


def test_root_with_class_outside_schema_raises():
    with pytest.raises(ConfigValidationError, match="expects Experiment"):
        instantiate({"$class": POINT, "x": 1, "y": 2}, schema=Experiment)


def test_root_without_class_is_validated_against_schema():
    with pytest.raises(ConfigValidationError, match=r"`seed` \(Experiment\)"):
        instantiate({"encoder": ENCODER, "seed": "many"}, schema=Experiment)
    with pytest.raises(ConfigValidationError, match="Missing required field"):
        instantiate({"seed": 1}, schema=Experiment)


def test_root_without_class_needs_a_dataclass_schema():
    with pytest.raises(ConfigValidationError, match="no dataclass schema"):
        instantiate({"x": 1, "y": 2}, schema=Point)


def test_root_without_class_or_schema_raises():
    with pytest.raises(ConfigValidationError, match="has no `\\$class`"):
        instantiate({"encoder": ENCODER})


def test_root_with_ref_raises_even_with_schema():
    with pytest.raises(ConfigValidationError, match="has no `\\$class`"):
        instantiate({"$ref": "tests.schemas.Encoder"}, schema=Encoder)


def test_schema_that_is_not_a_class_raises_type_error():
    with pytest.raises(TypeError, match="is not a class"):
        instantiate({"encoder": ENCODER}, schema=Experiment(Encoder()))  # pyright: ignore[reportArgumentType]


def test_schema_applies_after_overrides():
    experiment = instantiate(
        {"encoder": ENCODER}, schema=Experiment, overrides=["seed=3", "name=long"]
    )
    assert (experiment.seed, experiment.name) == (3, "long")


def test_schema_root_respects_allowed_modules():
    with pytest.raises(ConfigValidationError, match="allowed_modules"):
        instantiate({"encoder": ENCODER}, schema=Experiment, allowed_modules=[])


def test_prepare_root_without_class_defers_dataclass():
    make = prepare({"encoder": ENCODER}, schema=Experiment)
    assert isinstance(make, functools.partial)
    experiment = make(seed=9)
    assert type(experiment) is Experiment
    assert experiment.seed == 9


def test_prepare_root_without_class_defers_configurable():
    make = prepare({"width": 2}, schema=TypedEncoder)
    assert make().width == 2
    assert make(width=5).width == 5


def test_prepare_root_with_class_builds_subclass_of_schema():
    make = prepare(
        {"$class": f"{__name__}.LongExperiment", "encoder": ENCODER}, schema=Experiment
    )
    assert type(make()) is LongExperiment


def test_error_note_names_schema_for_root_without_class():
    with pytest.raises(ValueError, match="bad width") as info:
        instantiate({"width": -1}, schema=Failing)
    assert info.value.__notes__ == [f"while instantiating <root> ({__name__}.Failing)"]
