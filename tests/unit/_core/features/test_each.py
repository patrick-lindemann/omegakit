import re
from typing import Any

import pytest
from omegaconf import OmegaConf

from omegakit._core.errors import (
    EachTypeError,
    MergeCycleError,
    MergeReferenceError,
)
from omegakit._core.features.each import apply_each


def test_every_mapping_next_to_each_gets_it():
    config = OmegaConf.create(
        {
            "data": {
                "$each": {"n": 256, "noise": 0.1},
                "train": {"seed": 0},
                "validation": {"seed": 1, "n": 64},
            }
        }
    )
    config = apply_each(config)
    assert config.data == {
        "train": {"n": 256, "noise": 0.1, "seed": 0},
        "validation": {"n": 64, "noise": 0.1, "seed": 1},
    }
    assert list(config.data.train.keys()) == ["n", "noise", "seed"]


def test_each_merges_deeply():
    config = OmegaConf.create(
        {
            "$each": {"optimizer": {"lr": 0.1, "momentum": 0.9}},
            "model": {"optimizer": {"lr": 0.01}},
        }
    )
    config = apply_each(config)
    assert config.model == {"optimizer": {"lr": 0.01, "momentum": 0.9}}


def test_only_mappings_get_each():
    content = {
        "epochs": 10,
        "seeds": [{"value": 0}],
        "nothing": None,
        "data": "???",
        "alias": "${model}",
        "$meta": {"title": "Wide MLP"},
        "model": {},
    }
    config = OmegaConf.create({"$each": {"n": 256}, **content})
    config = apply_each(config)
    assert OmegaConf.to_container(config) == {**content, "model": {"n": 256}}


def test_each_does_not_reach_grandchildren():
    config = OmegaConf.create({"$each": {"n": 256}, "data": {"train": {}}})
    config = apply_each(config)
    assert config == {"data": {"train": {}, "n": 256}}


def test_an_inner_each_wins_over_an_outer_one():
    config = OmegaConf.create(
        {
            "$each": {"n": 256, "noise": 0.1},
            "data": {"$each": {"n": 64}, "train": {}},
        }
    )
    config = apply_each(config)
    assert config == {"data": {"n": 256, "noise": 0.1, "train": {"n": 64}}}


def test_applies_each_in_a_list_config():
    config = OmegaConf.create([{"$each": {"n": 256}, "train": {"seed": 0}}])
    config = apply_each(config)
    assert config == [{"train": {"n": 256, "seed": 0}}]


def test_a_relative_interpolation_resolves_in_each_mapping():
    config = OmegaConf.create(
        {
            "records": {
                "$each": {"path": "prefix/${.id}.h5"},
                "sphere": {"id": "sphere"},
                "cube": {"id": "cube"},
            }
        }
    )
    config = apply_each(config)
    assert config.records.sphere.path == "prefix/sphere.h5"
    assert config.records.cube.path == "prefix/cube.h5"


@pytest.mark.parametrize("is_reversed", [False, True])
def test_a_referenced_each_has_its_own_each_applied(is_reversed: bool):
    nodes = {
        "model": {"$each": "${shared}", "encoder": {"depth": 2}},
        "shared": {"$each": {"lr": 0.1}, "optimizer": {"momentum": 0.9}},
    }
    keys = list(reversed(nodes)) if is_reversed else list(nodes)
    config = OmegaConf.create({key: nodes[key] for key in keys})
    config = apply_each(config)
    assert config.model == {
        "encoder": {"optimizer": {"lr": 0.1, "momentum": 0.9}, "depth": 2}
    }


def test_part_of_a_config():
    config = OmegaConf.create(
        {
            "$each": {"n": 256},
            "shared": {"noise": 0.1},
            "data": {"$each": "${shared}", "train": {}},
        }
    )
    apply_each(config.data, copy=False)
    assert config == {
        "$each": {"n": 256},
        "shared": {"noise": 0.1},
        "data": {"train": {"noise": 0.1}},
    }


def test_the_default_returns_a_copy():
    content = {"$each": {"n": 256}, "train": {}}
    config = OmegaConf.create(content)
    applied_config = apply_each(config)
    assert applied_config is not config
    assert applied_config == {"train": {"n": 256}}
    assert config == content


def test_without_a_copy_the_config_itself_is_changed():
    config = OmegaConf.create({"$each": {"n": 256}, "train": {}})
    applied_config = apply_each(config, copy=False)
    assert applied_config is config
    assert config == {"train": {"n": 256}}


@pytest.mark.parametrize("each", [3, "text", None, "???", [{"n": 256}]])
def test_each_that_is_not_a_mapping_is_rejected(each: Any):
    config = OmegaConf.create({"data": {"$each": each, "train": {}}})
    with pytest.raises(EachTypeError) as error_info:
        apply_each(config)
    error_info.match(re.escape("at `data`"))


def test_reference_that_never_resolves_is_rejected():
    config = OmegaConf.create({"data": {"$each": "${nope}", "train": {}}})
    with pytest.raises(MergeReferenceError, match="nope"):
        apply_each(config)


def test_cycle_is_rejected():
    config = OmegaConf.create(
        {"a": {"$each": "${b}", "x": {}}, "b": {"$each": "${a}", "y": {}}}
    )
    with pytest.raises(MergeCycleError, match="`a` -> `b` -> `a`"):
        apply_each(config)


def test_a_failure_leaves_the_config_unchanged():
    content = {
        "data": {"$each": {"n": 256}, "train": {}},
        "model": {"$each": 3},
    }
    config = OmegaConf.create(content)
    with pytest.raises(EachTypeError):
        apply_each(config)
    assert config == content
