import pytest

from omegakit import load_config


def test_load_merges_base_with_node_winning(write_yaml):
    cfg = load_config(write_yaml("c.yaml", "$base:\n  a: 1\n  b: 2\nb: 20\n"))
    assert cfg.a == 1
    assert cfg.b == 20


def test_load_resolves_base_import_in_list_item(write_yaml):
    # The `stages:` pattern: a list item merges an imported `$base` under its own keys.
    write_yaml("defaults.yaml", "lr: 5\nsteps: 100\n")
    cfg = load_config(
        write_yaml(
            "main.yaml",
            "stages:\n  - $base: ~import defaults.yaml\n    steps: 3\n",
        )
    )
    assert cfg.stages[0].lr == 5
    assert cfg.stages[0].steps == 3


def test_load_merges_nested_base(write_yaml):
    cfg = load_config(
        write_yaml(
            "c.yaml",
            "model:\n  $base:\n    lr: 5\n    steps: 100\n  steps: 3\n",
        )
    )
    assert cfg.model.lr == 5
    assert cfg.model.steps == 3


def test_load_base_populated_by_import(write_yaml):
    write_yaml("defaults.yaml", "lr: 5\nsteps: 100\n")
    cfg = load_config(
        write_yaml(
            "main.yaml",
            "model:\n  $base: ~import defaults.yaml\n  steps: 3\n",
        )
    )
    # Imports resolve before base merging, so `$base: ~import ...` becomes a dict first.
    assert cfg.model.lr == 5
    assert cfg.model.steps == 3


def test_load_base_non_dict_raises(write_yaml):
    with pytest.raises(ValueError, match="is not a dictionary or a list"):
        load_config(write_yaml("c.yaml", "$base: 5\na: 1\n"))


def test_load_merges_list_base_with_later_winning(write_yaml):
    # A list `$base` merges its elements left to right; later elements win, and the
    # node's own keys win over all of them.
    cfg = load_config(
        write_yaml(
            "c.yaml",
            "$base:\n  - { a: 1, b: 1, c: 1 }\n  - { b: 2, c: 2 }\nc: 3\n",
        )
    )
    assert (cfg.a, cfg.b, cfg.c) == (1, 2, 3)


def test_load_merges_list_base_from_imports(write_yaml):
    write_yaml("globals.yaml", "seed: 42\nprecision: high\n")
    write_yaml("model.yaml", "model:\n  lr: 5\n")
    cfg = load_config(
        write_yaml(
            "main.yaml",
            "$base:\n  - ~import globals.yaml\n  - ~import model.yaml\nseed: 7\n",
        )
    )
    assert cfg.seed == 7
    assert cfg.precision == "high"
    assert cfg.model.lr == 5


def test_load_list_base_non_dict_element_raises(write_yaml):
    with pytest.raises(ValueError, match="must contain only dictionaries"):
        load_config(write_yaml("c.yaml", "$base:\n  - { a: 1 }\n  - 5\n"))


def test_load_top_level_interpolation_under_base_is_lazy(write_yaml):
    # A top-level `${...}` under a `$base` node must resolve lazily against the final
    # tree, not be baked at load time.
    write_yaml("lib.yaml", "a: 1\nb: ???\n")
    cfg = load_config(
        write_yaml(
            "main.yaml",
            "target: from_root\nnode:\n  $base: ~import lib.yaml\n  b: ${target}\n",
        )
    )
    assert cfg.node.b == "from_root"
    cfg.target = "changed"
    assert cfg.node.b == "changed"
