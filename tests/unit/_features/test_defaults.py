from typing import Any

import pytest
from omegaconf import OmegaConf

from omegakit._core.error import OmegaKitBaseException
from omegakit._core.merge import MergeCycleError, MergeReferenceError
from omegakit._features.defaults import (
    ConfigDefaultsError,
    DefaultsTypeError,
    apply_defaults,
)


def test_every_mapping_next_to_the_defaults_gets_them():
    config = OmegaConf.create(
        {
            "data": {
                "$defaults": {"n": 256, "noise": 0.1},
                "train": {"seed": 0},
                "validation": {"seed": 1, "n": 64},
            }
        }
    )
    config = apply_defaults(config)
    assert config.data == {
        "train": {"n": 256, "noise": 0.1, "seed": 0},
        "validation": {"n": 64, "noise": 0.1, "seed": 1},
    }
    assert list(config.data.train.keys()) == ["n", "noise", "seed"]


def test_defaults_merge_deeply():
    config = OmegaConf.create(
        {
            "$defaults": {"optimizer": {"lr": 0.1, "momentum": 0.9}},
            "model": {"optimizer": {"lr": 0.01}},
        }
    )
    config = apply_defaults(config)
    assert config.model == {"optimizer": {"lr": 0.01, "momentum": 0.9}}


def test_only_mappings_get_the_defaults():
    content = {
        "epochs": 10,
        "seeds": [{"value": 0}],
        "nothing": None,
        "data": "???",
        "alias": "${model}",
        "$meta": {"title": "Wide MLP"},
        "model": {},
    }
    config = OmegaConf.create({"$defaults": {"n": 256}, **content})
    config = apply_defaults(config)
    assert OmegaConf.to_container(config) == {**content, "model": {"n": 256}}


def test_defaults_do_not_reach_grandchildren():
    config = OmegaConf.create({"$defaults": {"n": 256}, "data": {"train": {}}})
    config = apply_defaults(config)
    assert config == {"data": {"train": {}, "n": 256}}


def test_inner_defaults_win_over_outer_ones():
    config = OmegaConf.create(
        {
            "$defaults": {"n": 256, "noise": 0.1},
            "data": {"$defaults": {"n": 64}, "train": {}},
        }
    )
    config = apply_defaults(config)
    assert config == {"data": {"n": 256, "noise": 0.1, "train": {"n": 64}}}


def test_applies_defaults_in_a_list_config():
    config = OmegaConf.create([{"$defaults": {"n": 256}, "train": {"seed": 0}}])
    config = apply_defaults(config)
    assert config == [{"train": {"n": 256, "seed": 0}}]


def test_a_relative_interpolation_resolves_in_each_mapping():
    config = OmegaConf.create(
        {
            "records": {
                "$defaults": {"path": "prefix/${.id}.h5"},
                "sphere": {"id": "sphere"},
                "cube": {"id": "cube"},
            }
        }
    )
    config = apply_defaults(config)
    assert config.records.sphere.path == "prefix/sphere.h5"
    assert config.records.cube.path == "prefix/cube.h5"


@pytest.mark.parametrize("is_reversed", [False, True])
def test_referenced_defaults_have_their_own_defaults_applied(is_reversed: bool):
    nodes = {
        "model": {"$defaults": "${shared}", "encoder": {"depth": 2}},
        "shared": {"$defaults": {"lr": 0.1}, "optimizer": {"momentum": 0.9}},
    }
    keys = list(reversed(nodes)) if is_reversed else list(nodes)
    config = OmegaConf.create({key: nodes[key] for key in keys})
    config = apply_defaults(config)
    assert config.model == {
        "encoder": {"optimizer": {"lr": 0.1, "momentum": 0.9}, "depth": 2}
    }


def test_part_of_a_config():
    config = OmegaConf.create(
        {
            "$defaults": {"n": 256},
            "shared": {"noise": 0.1},
            "data": {"$defaults": "${shared}", "train": {}},
        }
    )
    apply_defaults(config.data, copy=False)
    assert config == {
        "$defaults": {"n": 256},
        "shared": {"noise": 0.1},
        "data": {"train": {"noise": 0.1}},
    }


def test_the_default_returns_a_copy():
    content = {"$defaults": {"n": 256}, "train": {}}
    config = OmegaConf.create(content)
    applied_config = apply_defaults(config)
    assert applied_config is not config
    assert applied_config == {"train": {"n": 256}}
    assert config == content


def test_without_a_copy_the_config_itself_is_changed():
    config = OmegaConf.create({"$defaults": {"n": 256}, "train": {}})
    applied_config = apply_defaults(config, copy=False)
    assert applied_config is config
    assert config == {"train": {"n": 256}}


@pytest.mark.parametrize("defaults", [3, "text", None, "???", [{"n": 256}]])
def test_defaults_that_are_not_a_mapping_are_rejected(defaults: Any):
    config = OmegaConf.create({"data": {"$defaults": defaults, "train": {}}})
    with pytest.raises(DefaultsTypeError) as error_info:
        apply_defaults(config)
    assert error_info.value.__notes__ == ["  at `data`"]


def test_reference_that_never_resolves_is_rejected():
    config = OmegaConf.create({"data": {"$defaults": "${nope}", "train": {}}})
    with pytest.raises(MergeReferenceError, match="nope"):
        apply_defaults(config)


def test_cycle_is_rejected():
    config = OmegaConf.create(
        {"a": {"$defaults": "${b}", "x": {}}, "b": {"$defaults": "${a}", "y": {}}}
    )
    with pytest.raises(MergeCycleError, match="`a` -> `b` -> `a`"):
        apply_defaults(config)


def test_a_failure_leaves_the_config_unchanged():
    content = {
        "data": {"$defaults": {"n": 256}, "train": {}},
        "model": {"$defaults": 3},
    }
    config = OmegaConf.create(content)
    with pytest.raises(DefaultsTypeError):
        apply_defaults(config)
    assert config == content


def test_errors_are_also_builtin_errors():
    assert issubclass(DefaultsTypeError, ConfigDefaultsError)
    assert issubclass(DefaultsTypeError, OmegaKitBaseException)
    assert issubclass(DefaultsTypeError, TypeError)
