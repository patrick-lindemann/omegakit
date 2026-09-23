import functools
from typing import Any, assert_type

from omegaconf import DictConfig

from omegakit import instantiate, prepare
from tests.helpers import Point

# Checked by pyright only; pytest does not collect this module.


def check_instantiate_overloads(config: DictConfig) -> None:
    assert_type(instantiate(config), Any)
    assert_type(instantiate(config, Point), Point)
    assert_type(instantiate(config, Point, overrides=["x=1"]), Point)
    assert_type(instantiate({"$class": "a.B"}, overrides={"x": 1}), Any)


def check_prepare_overloads(config: DictConfig) -> None:
    assert_type(prepare(config), functools.partial[Any])
    assert_type(prepare(config, Point), functools.partial[Point])
    assert_type(prepare(config, Point, overrides=["x=1"]), functools.partial[Point])
