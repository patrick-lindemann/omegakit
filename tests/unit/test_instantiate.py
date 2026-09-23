import pytest
from omegaconf import OmegaConf

from omegakit import instantiate
from tests.helpers import (
    CONFIGURABLE_POINT,
    CONTAINER,
    POINT,
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
