import pytest
from omegaconf import OmegaConf

from omegakit._core.utils.walk import walk, walk_post_order, walk_pre_order


def _full_keys(nodes):
    return [node._get_full_key(None) for node in nodes]


def test_parent_comes_before_its_children_by_default():
    config = OmegaConf.create({"model": {"layers": [1, 2]}, "seed": 0})
    expected = ["", "model", "model.layers", "model.layers[0]", "model.layers[1]"]
    assert _full_keys(walk(config)) == [*expected, "seed"]
    assert _full_keys(walk_pre_order(config)) == [*expected, "seed"]


def test_children_come_before_their_parent_in_post_order():
    config = OmegaConf.create({"model": {"layers": [1, 2]}, "seed": 0})
    expected = ["model.layers[0]", "model.layers[1]", "model.layers", "model"]
    assert _full_keys(walk(config, "post-order")) == [*expected, "seed", ""]
    assert _full_keys(walk_post_order(config)) == [*expected, "seed", ""]


def test_value_that_is_missing_or_an_interpolation_is_not_read():
    config = OmegaConf.create({"lr": "???", "depth": "${nope}"})
    nodes = list(walk(config))
    assert [node._value() for node in nodes[1:]] == ["???", "${nope}"]


def test_unknown_order_is_rejected():
    config = OmegaConf.create({"seed": 0})
    with pytest.raises(ValueError, match="in-order"):
        list(walk(config, "in-order"))  # ty: ignore[invalid-argument-type]
