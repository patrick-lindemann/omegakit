import pytest

from omegakit import load_config


def test_load_merges_defaults_into_dict_siblings(write_yaml):
    cfg = load_config(
        write_yaml(
            "c.yaml",
            "node:\n  $defaults:\n    p: 1\n  a: {q: 2}\n  b: {q: 3}\n",
        )
    )
    assert (cfg.node.a.p, cfg.node.a.q) == (1, 2)
    assert (cfg.node.b.p, cfg.node.b.q) == (1, 3)


def test_load_defaults_skips_scalar_and_list_siblings(write_yaml):
    cfg = load_config(
        write_yaml(
            "c.yaml",
            "node:\n  $defaults:\n    p: 1\n  s: 5\n  l:\n    - {q: 2}\n  d: {}\n",
        )
    )
    assert cfg.node.s == 5
    assert "p" not in cfg.node.l[0]
    assert cfg.node.d.p == 1


def test_load_defaults_item_keys_win(write_yaml):
    cfg = load_config(
        write_yaml("c.yaml", "node:\n  $defaults:\n    p: 1\n  a: {p: 2}\n")
    )
    assert cfg.node.a.p == 2


def test_load_defaults_skips_special_keys(write_yaml):
    cfg = load_config(
        write_yaml(
            "c.yaml",
            "node:\n  $defaults:\n    p: 1\n  $meta:\n    author: x\n  a: {}\n",
        ),
        keep_meta=True,
    )
    assert "p" not in cfg.node["$meta"]
    assert cfg.node.a.p == 1


def test_load_defaults_non_dict_raises(write_yaml):
    with pytest.raises(ValueError, match="is not a dictionary"):
        load_config(write_yaml("c.yaml", "node:\n  $defaults: 5\n  a: {}\n"))


def test_load_nested_defaults_inner_wins(write_yaml):
    cfg = load_config(
        write_yaml(
            "c.yaml",
            "outer:\n"
            "  $defaults:\n"
            "    child:\n"
            "      q: 1\n"
            "  group:\n"
            "    $defaults:\n"
            "      q: 2\n"
            "    child: {}\n",
        )
    )
    assert cfg.outer.group.child.q == 2


def test_load_defaults_deep_merge(write_yaml):
    cfg = load_config(
        write_yaml(
            "c.yaml",
            "node:\n  $defaults:\n    opts: {a: 1, b: 2}\n  item:\n    opts: {b: 3}\n",
        )
    )
    assert (cfg.node.item.opts.a, cfg.node.item.opts.b) == (1, 3)


def test_load_defaults_populated_by_base_import(write_yaml):
    write_yaml("lib.yaml", "$defaults:\n  p: 1\n")
    cfg = load_config(
        write_yaml(
            "main.yaml",
            "node:\n  $base: ~import lib.yaml\n  item: {q: 2}\n",
        )
    )
    assert (cfg.node.item.p, cfg.node.item.q) == (1, 2)


def test_load_base_inside_defaults_assembled_before_distribution(write_yaml):
    cfg = load_config(
        write_yaml(
            "c.yaml",
            "node:\n  $defaults:\n    $base: {a: 1}\n    b: 2\n  item: {c: 3}\n",
        )
    )
    assert (cfg.node.item.a, cfg.node.item.b, cfg.node.item.c) == (1, 2, 3)


def test_load_defaults_sibling_base_resolved_first(write_yaml):
    cfg = load_config(
        write_yaml(
            "c.yaml",
            "node:\n  $defaults: {d: 1}\n  item:\n    $base: {x: 5}\n    y: 2\n",
        )
    )
    assert (cfg.node.item.x, cfg.node.item.y, cfg.node.item.d) == (5, 2, 1)


def test_load_defaults_relative_interpolation_resolves(write_yaml):
    cfg = load_config(
        write_yaml(
            "c.yaml",
            "records:\n"
            "  $defaults:\n"
            "    path: prefix/${.id}.h5\n"
            "  sphere: {id: sphere}\n"
            "  cube: {id: cube}\n",
        )
    )
    assert cfg.records.sphere.path == "prefix/sphere.h5"
    assert cfg.records.cube.path == "prefix/cube.h5"


def test_load_defaults_absolute_interpolation_resolves_from_root(write_yaml):
    cfg = load_config(
        write_yaml(
            "c.yaml",
            "base_dir: /data\n"
            "records:\n"
            "  $defaults:\n"
            "    path: ${base_dir}/${.id}.h5\n"
            "  sphere: {id: sphere}\n",
        )
    )
    assert cfg.records.sphere.path == "/data/sphere.h5"


def test_load_defaults_dropped_from_output(write_yaml):
    cfg = load_config(write_yaml("c.yaml", "node:\n  $defaults: {p: 1}\n  a: {}\n"))
    assert "$defaults" not in cfg.node
