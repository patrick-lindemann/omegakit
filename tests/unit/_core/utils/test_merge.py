import re
from typing import Any

import pytest
from omegaconf import DictConfig, OmegaConf
from omegaconf.errors import InterpolationResolutionError

from omegakit._core.errors import (
    ConfigMergeError,
)
from omegakit._core.utils.merge import merge_over, merge_under, walk_mergeable


def _remove_key(config: DictConfig, is_outer_first: bool = False) -> list[Any]:
    keys = []
    for node, _ in walk_mergeable(config, "$key", is_outer_first=is_outer_first):
        keys.append(node._key())
        del node["$key"]
    return keys


def test_merge_under_lets_the_node_win():
    config = OmegaConf.create({"model": {"hidden": 256}})
    first = OmegaConf.create({"hidden": 32, "depth": 2, "bias": True})
    second = OmegaConf.create({"depth": 4})
    merge_under(config.model, first, second)
    assert config == {"model": {"hidden": 256, "depth": 4, "bias": True}}


def test_merge_under_merges_nested_mappings_and_replaces_lists():
    config = OmegaConf.create({"model": {"hidden": 256}, "seeds": [0]})
    other = OmegaConf.create({"model": {"hidden": 32, "depth": 2}, "seeds": [1, 2]})
    merge_under(config, other)
    assert config == {"model": {"hidden": 256, "depth": 2}, "seeds": [0]}


def test_merge_under_keeps_the_node_in_its_place():
    config = OmegaConf.create({"model": {"hidden": 256}})
    node = config.model
    merge_under(node, OmegaConf.create({"depth": 2}))
    assert config.model is node


def test_merge_under_puts_the_merged_keys_first():
    config = OmegaConf.create({"seed": 0})
    merge_under(config, OmegaConf.create({"n": 256, "noise": 0.1}))
    assert list(config.keys()) == ["n", "noise", "seed"]


def test_merge_over_lets_the_others_win():
    config = OmegaConf.create({"model": {"hidden": 256, "bias": True}})
    merge_over(config.model, OmegaConf.create({"hidden": 32, "depth": 2}))
    assert config == {"model": {"hidden": 32, "bias": True, "depth": 2}}


def test_merge_under_keeps_values_unresolved():
    config = OmegaConf.create({"width": 8, "model": {"data": "???"}})
    merge_under(config.model, OmegaConf.create({"hidden": "${width}"}))
    assert OmegaConf.to_container(config.model) == {"hidden": "${width}", "data": "???"}
    config.width = 16
    assert config.model.hidden == 16


def test_walk_yields_children_before_parents():
    config = OmegaConf.create(
        {"$key": "root", "model": {"$key": "model", "layers": [{"$key": "layer"}]}}
    )
    values = []
    for node, value in walk_mergeable(config, "$key"):
        values.append(value)
        del node["$key"]
    assert values == ["layer", "model", "root"]


def test_walk_yields_a_referenced_node_first():
    config = OmegaConf.create(
        {
            "quick": {"$key": "${full}"},
            "full": {"$key": "${template.sweep}"},
            "template": {"$key": {"name": "template"}, "sweep": {"seeds": [0]}},
        }
    )
    assert _remove_key(config) == ["template", "full", "quick"]


def test_walk_does_not_wait_for_a_node_that_encloses_the_holder():
    config = OmegaConf.create(
        {"data": {"$key": {}, "train": {"n": 5}, "test": {"$key": "${..train}"}}}
    )
    assert _remove_key(config) == ["test", "data"]


def test_walk_outer_first_yields_parents_before_children():
    config = OmegaConf.create(
        {"$key": "root", "model": {"$key": "model", "layers": [{"$key": "layer"}]}}
    )
    values = []
    for node, value in walk_mergeable(config, "$key", is_outer_first=True):
        values.append(value)
        del node["$key"]
    assert values == ["root", "model", "layer"]


def test_walk_outer_first_yields_a_node_after_its_replaced_children():
    config = OmegaConf.create({"data": {"$key": 1, "test": {"$key": 2}}})
    values = []
    for node, value in walk_mergeable(config, "$key", is_outer_first=True):
        values.append(value)
        del node["$key"]
        # Replaced, as a merge replaces the children of the node it is given
        if value == 1:
            node.test = {"$key": 3}
    assert values == [1, 3]


def test_walk_outer_first_does_not_wait_for_a_node_whose_key_holds_the_holder():
    config = OmegaConf.create({"model": {"$key": {"$key": {}, "hidden": 32}}})
    assert _remove_key(config, is_outer_first=True) == ["$key", "model"]


def test_walk_outer_first_rejects_a_node_that_reads_a_node_inside_it():
    config = OmegaConf.create({"data": {"$key": "${data.test}", "test": {"$key": {}}}})
    with pytest.raises(
        ConfigMergeError, match=re.escape("`data` -> `data.test` -> `data`")
    ):
        _remove_key(config, is_outer_first=True)


def test_walk_yields_a_reference_to_a_key_that_appears_later():
    config = OmegaConf.create({"quick": {"$key": "${full.sweep}"}, "full": {"$key": 1}})
    values = []
    for node, value in walk_mergeable(config, "$key"):
        values.append(value)
        del node["$key"]
        if value == 1:
            node.sweep = {"seeds": [0]}
    assert values == [1, {"seeds": [0]}]


def test_walk_yields_a_missing_value_as_it_is():
    config = OmegaConf.create({"model": {"$key": "???"}})
    for node, value in walk_mergeable(config, "$key"):
        assert value == "???"
        del node["$key"]


def test_walk_rejects_a_reference_that_never_resolves():
    config = OmegaConf.create({"model": {"$key": "${nope}"}, "data": {"$key": 1}})
    with pytest.raises(ConfigMergeError, match="nope") as error_info:
        _remove_key(config)
    error_info.match(re.escape("at `model`"))
    assert isinstance(error_info.value.__cause__, InterpolationResolutionError)


def test_walk_rejects_a_cycle_and_names_only_its_nodes():
    config = OmegaConf.create(
        {
            "waiting": {"$key": "${a}"},
            "a": {"$key": "${b}"},
            "b": {"items": [{"$key": "${a}"}]},
        }
    )
    with pytest.raises(ConfigMergeError) as error_info:
        _remove_key(config)
    assert "`a` -> `b.items[0]` -> `a`" in str(error_info.value)
    assert "waiting" not in str(error_info.value)
