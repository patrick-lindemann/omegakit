from omegaconf import DictConfig, ListConfig, OmegaConf

from omegakit import walk


def test_walk_yields_the_root():
    config = OmegaConf.create({"a": 1})
    assert [node for node in walk(config)] == [config]


def test_walk_yields_nested_mappings():
    config = OmegaConf.create({"a": {"b": {"c": 1}}})
    assert [dict(node) for node in walk(config)] == [
        {"a": {"b": {"c": 1}}},
        {"b": {"c": 1}},
        {"c": 1},
    ]


def test_walk_descends_into_lists():
    config = OmegaConf.create({"items": [{"a": 1}, {"b": 2}]})
    assert {"a": 1} in [dict(node) for node in walk(config)]
    assert {"b": 2} in [dict(node) for node in walk(config)]


def test_walk_accepts_a_list_root():
    config = OmegaConf.create([{"a": 1}])
    assert [dict(node) for node in walk(config)] == [{"a": 1}]


def test_walk_skips_scalars():
    config = OmegaConf.create({"a": 1, "b": "x", "c": None, "d": [1, 2]})
    assert [node for node in walk(config)] == [config]


def test_walk_yields_an_interpolated_node_once():
    # `${target}` must not be resolved into a second, independent node
    config = OmegaConf.create({"target": {"a": 1}, "alias": "${target}"})
    nodes = [node for node in walk(config) if "a" in node]
    assert len(nodes) == 1
    assert nodes[0] is config._get_node("target")


def test_walk_reaches_a_node_only_referenced_by_interpolation():
    config = OmegaConf.create(
        {"evaluations": [{"every_n_epochs": 10}], "callback": "${evaluations}"}
    )
    for node in walk(config):
        if "every_n_epochs" in node:
            node["every_n_epochs"] = 1
    assert config["callback"][0]["every_n_epochs"] == 1


def test_walk_reflects_value_mutation_during_iteration():
    config = OmegaConf.create({"a": {"n": 10}, "b": {"n": 10}})
    for node in walk(config):
        if "n" in node:
            node["n"] = 1
    assert config["a"]["n"] == 1
    assert config["b"]["n"] == 1


def test_walk_yields_only_dict_configs():
    config = OmegaConf.create({"items": [{"a": 1}], "nested": [[{"b": 2}]]})
    assert all(isinstance(node, DictConfig) for node in walk(config))
    assert not any(isinstance(node, ListConfig) for node in walk(config))
