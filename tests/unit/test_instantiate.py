import pytest
from omegaconf import OmegaConf

from omegakit import instantiate
from tests.helpers import (
    CONFIGURABLE_POINT,
    CONTAINER,
    POINT,
    RECORDER,
    ConfigurablePoint,
    Container,
    Point,
)


def test_instantiate_builds_object():
    obj = instantiate({"$class": POINT, "x": 1, "y": 2})
    assert isinstance(obj, Point)
    assert (obj.x, obj.y) == (1, 2)


def test_instantiate_uses_from_config():
    obj = instantiate({"$class": CONFIGURABLE_POINT, "x": 3, "y": 4})
    assert isinstance(obj, ConfigurablePoint)
    assert (obj.x, obj.y) == (3, 4)


def test_instantiate_builds_nested_class():
    obj = instantiate(
        {
            "$class": CONTAINER,
            "name": "c",
            "point": {"$class": POINT, "x": 1, "y": 2},
        }
    )
    assert isinstance(obj, Container)
    assert isinstance(obj.point, Point)
    assert obj.point.x == 1


def test_instantiate_missing_class_raises():
    with pytest.raises(ValueError, match="Cannot instantiate config with no"):
        instantiate({"x": 1})


def test_instantiate_unknown_class_raises():
    with pytest.raises(ImportError):
        instantiate({"$class": "tests.helpers.DoesNotExist"})


def test_instantiate_applies_overrides():
    obj = instantiate({"$class": POINT, "x": 1, "y": 2}, overrides={"x": 10})
    assert obj.x == 10


def test_class_override_selects_new_class():
    cfg = OmegaConf.create({"$class": "missing.Original", "x": 1, "y": 2})
    obj = instantiate(cfg, overrides={"$class": POINT})
    assert isinstance(obj, Point)
    assert cfg["$class"] == "missing.Original"


def test_instantiate_does_not_mutate_input():
    config = OmegaConf.create({"$class": POINT, "x": "${y}", "y": 2})
    before = OmegaConf.to_yaml(config)
    instantiate(config)
    instantiate(config, overrides=["y=3"])
    assert OmegaConf.to_yaml(config) == before


def test_instantiate_resolves_interpolation():
    obj = instantiate(OmegaConf.create({"$class": POINT, "x": "${y}", "y": 2}))
    assert obj.x == 2


def test_instantiate_never_passes_meta():
    obj = instantiate(
        {
            "$class": CONTAINER,
            "$meta": {"a": 1},
            "name": "c",
            "point": {"$class": POINT, "$meta": 1, "x": 1, "y": 2},
        }
    )
    assert isinstance(obj.point, Point)


def test_instantiate_builds_classes_in_lists():
    obj = instantiate(
        {"$class": CONTAINER, "name": "c", "point": [{"$class": POINT, "x": 1, "y": 2}]}
    )
    assert isinstance(obj.point[0], Point)


def test_instantiate_duck_typed_from_config_receives_built_children():
    config, kwargs = instantiate(
        {"$class": RECORDER, "a": 1, "child": {"$class": POINT, "x": 1, "y": 2}}
    )
    assert config["a"] == 1
    assert isinstance(config["child"], Point)
    assert kwargs == {}


def test_instantiate_unknown_module_raises():
    with pytest.raises(ModuleNotFoundError):
        instantiate({"$class": "tests.does_not_exist.Thing"})
