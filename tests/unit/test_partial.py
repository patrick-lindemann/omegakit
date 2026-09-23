import functools

from omegakit import instantiate, prepare
from tests.helpers import (
    POINT,
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
