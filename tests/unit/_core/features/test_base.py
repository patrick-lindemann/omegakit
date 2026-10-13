import re
from typing import Any

import pytest
from omegaconf import OmegaConf
from omegaconf.errors import ReadonlyConfigError

from omegakit._core.errors import (
    ConfigMergeError,
)
from omegakit._core.features.base import merge_bases


def test_own_keys_win_over_the_base():
    config = OmegaConf.create(
        {
            "$base": {"model": {"hidden": 32, "layers": 2}, "epochs": 200},
            "model": {"hidden": 256},
        }
    )
    config = merge_bases(config)
    assert config == {"model": {"hidden": 256, "layers": 2}, "epochs": 200}


def test_lists_are_replaced_not_joined():
    config = OmegaConf.create(
        {"quick": {"$base": {"seeds": [0, 1, 2], "hidden": [32, 256]}, "seeds": [0]}}
    )
    config = merge_bases(config)
    assert config.quick == {"seeds": [0], "hidden": [32, 256]}


def test_later_items_of_a_list_win():
    config = OmegaConf.create(
        {"model": {"$base": [{"hidden": 32, "depth": 2}, {"depth": 4}], "bias": True}}
    )
    config = merge_bases(config)
    assert config.model == {"hidden": 32, "depth": 4, "bias": True}


def test_merges_bases_in_a_list_config():
    config = OmegaConf.create([{"$base": {"depth": 2}, "hidden": 32}])
    config = merge_bases(config)
    assert config == [{"depth": 2, "hidden": 32}]


def test_a_child_is_merged_before_its_parent():
    config = OmegaConf.create(
        {
            "$base": {"model": {"hidden": 32, "depth": 2}},
            "model": {"$base": {"depth": 4}},
        }
    )
    config = merge_bases(config)
    assert config.model == {"hidden": 32, "depth": 4}


def test_a_parent_waits_for_a_child_that_waits():
    config = OmegaConf.create(
        {
            "outer": {
                "$base": {"inner": {"lr": 0.5, "decay": 0.1}},
                "inner": {"$base": "${late}"},
            },
            "late": {"$base": {"lr": 0.1}},
        }
    )
    config = merge_bases(config)
    assert config.outer == {"inner": {"lr": 0.1, "decay": 0.1}}


def test_a_base_inside_a_base_is_merged_first():
    config = OmegaConf.create(
        {"model": {"$base": {"$base": {"hidden": 32, "depth": 2}, "depth": 4}}}
    )
    config = merge_bases(config)
    assert config.model == {"hidden": 32, "depth": 4}


def test_a_referenced_base_is_a_copy():
    config = OmegaConf.create(
        {"full": {"seeds": [0, 1, 2]}, "quick": {"$base": "${full}", "fast": True}}
    )
    config = merge_bases(config)
    config.full.seeds = [9]
    assert config.quick == {"seeds": [0, 1, 2], "fast": True}


@pytest.mark.parametrize("is_reversed", [False, True])
def test_a_reference_sees_the_merged_node_wherever_it_stands(is_reversed: bool):
    nodes = {
        "quick": {"$base": "${full.sweep}"},
        "full": {"$base": {"sweep": {"seeds": [0, 1], "repeats": 3}}, "sweep": {}},
        "wide": {"$base": ["${quick}", {"hidden": 256}]},
    }
    keys = list(reversed(nodes)) if is_reversed else list(nodes)
    config = OmegaConf.create({key: nodes[key] for key in keys})
    config = merge_bases(config)
    assert config.quick == {"seeds": [0, 1], "repeats": 3}
    assert config.wide == {"seeds": [0, 1], "repeats": 3, "hidden": 256}


def test_a_reference_to_a_later_list_item():
    config = OmegaConf.create(
        {"stages": [{"$base": "${stages[1]}", "epochs": 1}, {"$base": {"lr": 0.1}}]}
    )
    config = merge_bases(config)
    assert config.stages == [{"lr": 0.1, "epochs": 1}, {"lr": 0.1}]


def test_a_reference_sees_an_enclosing_node_as_written():
    config = OmegaConf.create(
        {
            "data": {
                "$base": {"train": {"n": 1, "noise": 0.1}},
                "train": {"n": 5},
                "test": {"$base": "${..train}"},
            }
        }
    )
    config = merge_bases(config)
    assert config.data == {"train": {"n": 5, "noise": 0.1}, "test": {"n": 5}}


def test_a_base_reached_through_an_interpolation_is_merged_too():
    config = OmegaConf.create(
        {
            "template": {"optimizer": "${sgd}"},
            "model": {"$base": "${template}", "optimizer": {"lr": 0.1}},
            "sgd": {"$base": {"momentum": 0.9}, "nesterov": True},
        }
    )
    config = merge_bases(config)
    assert config.model == {"optimizer": {"momentum": 0.9, "nesterov": True, "lr": 0.1}}


def test_values_stay_unresolved():
    config = OmegaConf.create(
        {
            "width": 8,
            "model": {
                "$base": {"hidden": "${width}", "out": "${.hidden}"},
                "data": "???",
            },
        }
    )
    config = merge_bases(config)
    assert OmegaConf.to_container(config.model) == {
        "hidden": "${width}",
        "out": "${.hidden}",
        "data": "???",
    }
    config.width = 16
    assert config.model.out == 16


def test_an_own_missing_value_does_not_hide_the_base():
    config = OmegaConf.create({"model": {"$base": {"hidden": 32}, "hidden": "???"}})
    config = merge_bases(config)
    assert config.model == {"hidden": 32}


def test_part_of_a_config():
    config = OmegaConf.create(
        {
            "data": {"$base": {"n": 256}},
            "experiment": {
                "small": {"$base": {"hidden": 32}},
                "copy": {"$base": "${experiment.small}"},
            },
        }
    )
    merge_bases(config.experiment, copy=False)
    assert config == {
        "data": {"$base": {"n": 256}},
        "experiment": {"small": {"hidden": 32}, "copy": {"hidden": 32}},
    }


def test_the_default_returns_a_copy():
    content = {"model": {"$base": {"hidden": 32}}}
    config = OmegaConf.create(content)
    merged_config = merge_bases(config)
    assert merged_config is not config
    assert merged_config == {"model": {"hidden": 32}}
    assert config == content


def test_without_a_copy_the_config_itself_is_merged():
    config = OmegaConf.create({"model": {"$base": {"hidden": 32}}})
    merged_config = merge_bases(config, copy=False)
    assert merged_config is config
    assert config == {"model": {"hidden": 32}}


def test_a_copied_part_of_a_config_has_its_own_root():
    content = {
        "small": {"hidden": 32},
        "experiment": {"model": {"$base": "${small}"}},
    }
    config = OmegaConf.create(content)
    merged_config = merge_bases(config.experiment)
    assert merged_config == {"model": {"hidden": 32}}
    assert merged_config._get_root() is not config
    assert config == content


@pytest.mark.parametrize("base", [3, "text", None, "???", [{"depth": 2}, 3], ["???"]])
def test_base_that_holds_no_mappings_is_rejected(base: Any):
    config = OmegaConf.create({"models": [{"$base": base}]})
    with pytest.raises(ConfigMergeError) as error_info:
        merge_bases(config)
    error_info.match(re.escape("at `models[0]`"))


def test_reference_that_never_resolves_is_rejected():
    config = OmegaConf.create({"model": {"$base": "${nope}"}})
    with pytest.raises(ConfigMergeError, match="nope"):
        merge_bases(config)


def test_cycle_is_rejected():
    config = OmegaConf.create({"a": {"$base": "${b}"}, "b": {"$base": "${a}"}})
    with pytest.raises(ConfigMergeError, match="`a` -> `b` -> `a`"):
        merge_bases(config)


def test_a_failure_leaves_the_config_unchanged():
    content = {"model": {"$base": {"hidden": 32}}, "data": {"$base": 3}}
    config = OmegaConf.create(content)
    with pytest.raises(ConfigMergeError):
        merge_bases(config)
    assert config == content


def test_a_read_only_config_keeps_its_bases():
    content = {"model": {"$base": {"hidden": 32}}}
    config = OmegaConf.create(content)
    OmegaConf.set_readonly(config, True)
    with pytest.raises(ReadonlyConfigError):
        merge_bases(config)
    assert config == content
