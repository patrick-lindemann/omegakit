import pytest
from omegaconf.errors import MissingMandatoryValue

from omegakit import instantiate, prepare
from tests import schemas

# Contracts: §10 Typed configs (from_config).

MODEL = "tests.schemas.Model"


def test_from_config_default_passes_fields_to_constructor():
    obj = schemas.TypedEncoder.from_config(schemas.EncoderConfig(width=3))
    assert obj.width == 3


def test_from_config_default_call_time_arguments_win():
    obj = schemas.TypedEncoder.from_config(schemas.EncoderConfig(width=3), width=5)
    assert obj.width == 5


def test_from_config_receives_typed_config():
    model = instantiate({"$class": MODEL, "kind": "B", "depth": "3"}, schemas.Model)
    assert isinstance(model.kind, schemas.B)
    assert model.depth == 3


def test_from_config_receives_built_object_fields():
    model = instantiate(
        {"$class": MODEL, "depth": 1, "encoder": {"$class": "tests.schemas.Encoder"}}
    )
    assert isinstance(model.encoder, schemas.Encoder)


def test_from_config_factory_returns_subclass():
    assert isinstance(
        instantiate({"$class": "tests.schemas.Animal", "x": 1}), schemas.Dog
    )
    assert isinstance(
        instantiate({"$class": "tests.schemas.Animal", "x": 0}), schemas.Cat
    )


def test_from_config_call_time_arguments_reach_typed_from_config():
    model = prepare({"$class": MODEL, "depth": 1})(params=[1, 2])
    assert model.extra == {"params": [1, 2]}


def test_from_config_call_time_arguments_reach_default_from_config():
    partial = prepare({"$class": "tests.schemas.TypedEncoder", "width": 1})
    assert partial(width=4).width == 4


def test_from_config_missing_value_never_flows_through_a_partial():
    with pytest.raises(MissingMandatoryValue):
        prepare({"$class": MODEL, "depth": "???"})


def test_from_config_direct_raw_call_still_works():
    assert schemas.TypedEncoder.from_config({"width": 2}).width == 2  # type: ignore[arg-type]
