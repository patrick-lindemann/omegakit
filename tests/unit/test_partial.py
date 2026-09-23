import functools

from omegakit import instantiate, prepare
from tests.helpers import (
    CONTAINER,
    POINT,
    RECORDER,
    Point,
)


def test_instantiate_partial_flag_returns_partial():
    partial = instantiate({"$class": POINT, "$partial": True, "x": 1})
    assert isinstance(partial, functools.partial)
    obj = partial(y=2)
    assert isinstance(obj, Point)
    assert (obj.x, obj.y) == (1, 2)


def test_prepare_returns_partial():
    partial = prepare({"$class": POINT, "x": 5})
    assert isinstance(partial, functools.partial)
    assert partial(y=6).y == 6


def test_partial_false_is_not_a_constructor_argument():
    obj = instantiate({"$class": POINT, "$partial": False, "x": 1, "y": 2})
    assert isinstance(obj, Point)


def test_partial_nested_stays_partial():
    obj = instantiate(
        {"$class": CONTAINER, "name": "c", "point": {"$class": POINT, "$partial": True}}
    )
    assert isinstance(obj.point, functools.partial)
    assert obj.point(x=1, y=2).x == 1


def test_prepare_builds_nested_objects_immediately():
    partial = prepare({"$class": CONTAINER, "point": {"$class": POINT, "x": 1, "y": 2}})
    assert isinstance(partial.keywords["point"], Point)


def test_partial_call_time_argument_wins_for_plain_class():
    assert prepare({"$class": POINT, "x": 1, "y": 2})(x=5).x == 5


def test_partial_call_time_arguments_reach_duck_typed_from_config():
    config, kwargs = prepare({"$class": RECORDER, "a": 1})(b=2)
    assert config == {"a": 1}
    assert kwargs == {"b": 2}
