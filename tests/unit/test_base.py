import pytest
from omegaconf.errors import InterpolationKeyError

from omegakit import ConfigValidationError, load_config

# Contracts: §1 Pipeline order, §2 Precedence, §3 Resolution timing.


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
    with pytest.raises(ConfigValidationError, match="is not a dictionary or a list"):
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


def test_load_base_errors_name_the_node_path(write_yaml):
    path = write_yaml("c.yaml", "outer:\n  inner:\n    $base: 5\n    token: abc\n")
    with pytest.raises(ConfigValidationError, match=r"`outer\.inner`") as info:
        load_config(path)
    assert "abc" not in str(info.value)
    path = write_yaml("d.yaml", "$base: [5]\ntoken: abc\n")
    with pytest.raises(ConfigValidationError, match="`<root>`") as info:
        load_config(path)
    assert "abc" not in str(info.value)


def test_load_list_base_non_dict_element_raises(write_yaml):
    with pytest.raises(ConfigValidationError, match="must contain only dictionaries"):
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


def test_base_is_dropped_from_output(write_yaml):
    cfg = load_config(write_yaml("c.yaml", "n:\n  $base: {a: 1}\n"))
    assert "$base" not in cfg.n


def test_base_nested_merged_before_parent(write_yaml):
    cfg = load_config(
        write_yaml(
            "c.yaml",
            "n:\n  $base:\n    child: {a: 1, b: 1}\n  child:\n    $base: {b: 2}\n",
        )
    )
    assert dict(cfg.n.child) == {"a": 1, "b": 2}


def test_base_interpolation_to_earlier_sibling(write_yaml):
    cfg = load_config(
        write_yaml("c.yaml", "_common: {lr: 1}\nm:\n  $base: ${_common}\n  x: 2\n")
    )
    assert (cfg.m.lr, cfg.m.x) == (1, 2)


def test_base_relative_interpolation_resolves_at_final_position(write_yaml):
    cfg = load_config(write_yaml("c.yaml", "n:\n  $base: {b: '${.a}'}\n  a: 7\n"))
    assert cfg.n.b == 7


def test_base_interpolation_to_later_sibling_with_its_own_base(write_yaml):
    cfg = load_config(
        write_yaml("c.yaml", "m:\n  $base: ${c}\nc:\n  $base: {a: 1}\n  b: 2\n")
    )
    assert dict(cfg.m) == {"a": 1, "b": 2}


def test_base_interpolation_to_key_created_by_a_later_base(write_yaml):
    cfg = load_config(
        write_yaml("c.yaml", "m:\n  $base: ${c.x}\nc:\n  $base:\n    x: {a: 1}\n")
    )
    assert dict(cfg.m) == {"a": 1}


def test_base_chain_through_list_valued_base(write_yaml):
    cfg = load_config(
        write_yaml(
            "c.yaml",
            "m:\n  $base: ['${c}', {z: 1}]\nc:\n  $base: ${d}\nd:\n  $base: {a: 1}\n",
        )
    )
    assert dict(cfg.m) == {"a": 1, "z": 1}


def test_base_parent_waits_for_a_waiting_child(write_yaml):
    cfg = load_config(
        write_yaml(
            "c.yaml",
            "outer:\n  $base: {q: 1}\n  inner:\n    $base: ${c}\nc:\n  $base: {a: 1}\n",
        )
    )
    assert dict(cfg.outer.inner) == {"a": 1}
    assert cfg.outer.q == 1


def test_base_cycle_raises(write_yaml):
    path = write_yaml("c.yaml", "m:\n  $base: ${c}\nc:\n  $base: ${m}\n")
    with pytest.raises(ConfigValidationError, match=r"cycle between `m`, `c`"):
        load_config(path)


def test_base_interpolation_to_unknown_key_raises_a_config_error(write_yaml):
    with pytest.raises(ConfigValidationError, match="nope") as info:
        load_config(write_yaml("c.yaml", "m:\n  $base: ${nope}\n"))
    assert isinstance(info.value.__cause__, InterpolationKeyError)
