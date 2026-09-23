import functools

import pytest
from omegaconf import OmegaConf
from omegaconf.errors import MissingMandatoryValue

from config_compose import instantiate, prepare
from tests.helpers import ConfigurablePoint, Container, Point

POINT = "tests.helpers.Point"
CONFIGURABLE_POINT = "tests.helpers.ConfigurablePoint"
CONTAINER = "tests.helpers.Container"


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


def test_instantiate_ref_imports_object():
    obj = instantiate({"$class": POINT, "x": {"$ref": "builtins.int"}, "y": 2})
    assert obj.x is int


def test_instantiate_ref_with_extra_keys_raises():
    with pytest.raises(ValueError):
        instantiate(
            {"$class": POINT, "x": {"$ref": "builtins.int", "extra": 1}, "y": 2}
        )


def test_instantiate_missing_class_raises():
    with pytest.raises(ValueError):
        instantiate({"x": 1})


def test_instantiate_unknown_class_raises():
    with pytest.raises(ImportError):
        instantiate({"$class": "tests.helpers.DoesNotExist"})


def test_instantiate_partial_flag_returns_partial():
    partial = instantiate({"$class": POINT, "$partial": True, "x": 1})
    assert isinstance(partial, functools.partial)
    obj = partial(y=2)
    assert isinstance(obj, Point)
    assert (obj.x, obj.y) == (1, 2)


def test_instantiate_raises_on_missing_value():
    # `???` marks a consumer fill-in point; it must fail loudly rather than pass the
    # literal string "???" to the constructor.
    config = OmegaConf.create({"$class": POINT, "x": "???", "y": 2})
    with pytest.raises(MissingMandatoryValue):
        instantiate(config)


def test_instantiate_applies_overrides():
    obj = instantiate({"$class": POINT, "x": 1, "y": 2}, overrides={"x": 10})
    assert obj.x == 10


def test_prepare_returns_partial():
    partial = prepare({"$class": POINT, "x": 5})
    assert isinstance(partial, functools.partial)
    assert partial(y=6).y == 6


def test_partial_false_is_not_a_constructor_argument():
    obj = instantiate({"$class": POINT, "$partial": False, "x": 1, "y": 2})
    assert isinstance(obj, Point)


def test_class_override_selects_new_class():
    cfg = OmegaConf.create({"$class": "missing.Original", "x": 1, "y": 2})
    obj = instantiate(cfg, overrides={"$class": POINT})
    assert isinstance(obj, Point)
    assert cfg["$class"] == "missing.Original"
