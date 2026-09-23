from pathlib import Path

import pytest
from omegaconf import OmegaConf
from omegaconf.errors import InterpolationKeyError, InterpolationResolutionError

from omegakit import load_config


def test_load_resolves_import(write_yaml):
    write_yaml("base.yaml", "x: 10\n")
    cfg = load_config(write_yaml("main.yaml", "foo: ~import base.yaml\n"))
    assert cfg.foo.x == 10


def test_load_circular_import_raises(tmp_path: Path, write_yaml):
    write_yaml("a.yaml", "foo: ~import b.yaml\n")
    write_yaml("b.yaml", "bar: ~import a.yaml\n")
    with pytest.raises(ValueError, match="Circular import"):
        load_config(tmp_path / "a.yaml")


def test_load_import_selects_subnode(write_yaml):
    write_yaml("base.yaml", "opt:\n  lr: 5\nother: 2\n")
    cfg = load_config(write_yaml("main.yaml", 'foo: "~import base.yaml#opt"\n'))
    assert cfg.foo.lr == 5
    assert "other" not in cfg.foo


def test_load_resolves_import_in_list(write_yaml):
    write_yaml("leaf.yaml", "v: 42\n")
    cfg = load_config(
        write_yaml("main.yaml", "nodes:\n  - ~import leaf.yaml\n  - other\n")
    )
    assert cfg.nodes[0].v == 42
    assert cfg.nodes[1] == "other"


def test_load_import_selects_subnode_in_list(write_yaml):
    write_yaml("base.yaml", "opt:\n  lr: 5\nother: 2\n")
    cfg = load_config(write_yaml("main.yaml", 'nodes:\n  - "~import base.yaml#opt"\n'))
    assert cfg.nodes[0].lr == 5
    assert "other" not in cfg.nodes[0]


def test_load_resolves_nested_imports(write_yaml):
    write_yaml("leaf.yaml", "v: 42\n")
    write_yaml("mid.yaml", "x: ~import leaf.yaml\n")
    cfg = load_config(write_yaml("main.yaml", "y: ~import mid.yaml\n"))
    assert cfg.y.x.v == 42


def test_load_import_absolute_path(write_yaml):
    leaf = write_yaml("leaf.yaml", "v: 42\n")
    cfg = load_config(write_yaml("sub/main.yaml", f"foo: ~import {leaf}\n"))
    assert cfg.foo.v == 42


def test_load_import_resolves_config_interpolation(tmp_path: Path, write_yaml):
    write_yaml("leaf.yaml", "v: 42\n")
    cfg = load_config(
        write_yaml(
            "main.yaml",
            f"base_dir: {tmp_path}\nfoo: ~import ${{base_dir}}/leaf.yaml\n",
        )
    )
    assert cfg.foo.v == 42


def test_load_import_resolves_resolver_interpolation(
    tmp_path: Path, write_yaml, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("GRASPDIFF_TEST_IMPORT_DIR", str(tmp_path))
    write_yaml("leaf.yaml", "v: 42\n")
    cfg = load_config(
        write_yaml(
            "main.yaml",
            "foo: ~import ${oc.env:GRASPDIFF_TEST_IMPORT_DIR}/leaf.yaml\n",
        )
    )
    assert cfg.foo.v == 42


def test_load_import_resolves_relative_interpolation(write_yaml):
    write_yaml("sub/leaf.yaml", "v: 42\n")
    cfg = load_config(
        write_yaml(
            "main.yaml",
            "node:\n  dir: sub\n  foo: ~import ${.dir}/leaf.yaml\n",
        )
    )
    assert cfg.node.foo.v == 42


def test_load_import_resolves_interpolation_in_list(tmp_path: Path, write_yaml):
    write_yaml("leaf.yaml", "v: 42\n")
    cfg = load_config(
        write_yaml(
            "main.yaml",
            f"base_dir: {tmp_path}\nnodes:\n  - ~import ${{base_dir}}/leaf.yaml\n",
        )
    )
    assert cfg.nodes[0].v == 42


def test_load_import_unresolvable_interpolation_raises(write_yaml):
    with pytest.raises(InterpolationResolutionError):
        load_config(write_yaml("main.yaml", "foo: ~import ${missing}/leaf.yaml\n"))


def test_load_import_resolves_relative_to_importer(write_yaml):
    write_yaml("sub/leaf.yaml", "v: 7\n")
    write_yaml("sub/mid.yaml", "bar: ~import leaf.yaml\n")
    cfg = load_config(write_yaml("main.yaml", "foo: ~import sub/mid.yaml\n"))
    # `leaf.yaml` must resolve relative to sub/ (the importer), not the top dir.
    assert cfg.foo.bar.v == 7


def test_load_leaf_import_resolves_against_root(write_yaml):
    # An imported leaf interpolation resolves against the CONSUMER root, like a
    # container import — not against the imported file's own scope.
    write_yaml("base.yaml", "p: base_p\nq: ${p}\n")
    cfg = load_config(
        write_yaml("main.yaml", 'leaf: "~import base.yaml#q"\np: root_p\n')
    )
    assert cfg.leaf == "root_p"


def test_import_selects_list_index(write_yaml):
    write_yaml("lib.yaml", "a:\n  b:\n    - {v: 0}\n    - {v: 1}\n")
    cfg = load_config(write_yaml("main.yaml", 'n: "~import lib.yaml#a.b.1"\n'))
    assert cfg.n.v == 1


def test_import_whole_list_file(write_yaml):
    write_yaml("items.yaml", "- 1\n- 2\n")
    cfg = load_config(write_yaml("main.yaml", "n: ~import items.yaml\n"))
    assert list(cfg.n) == [1, 2]


def test_import_ignores_surrounding_whitespace(write_yaml):
    write_yaml("lib.yaml", "c: 3\n")
    cfg = load_config(write_yaml("main.yaml", 'n: "~import   lib.yaml#  c  "\n'))
    assert cfg.n == 3


def test_import_prefix_only_counts_at_the_start(write_yaml):
    cfg = load_config(write_yaml("main.yaml", 'n: "see ~import lib.yaml"\n'))
    assert cfg.n == "see ~import lib.yaml"


def test_import_missing_node_raises(write_yaml):
    write_yaml("lib.yaml", "a: 1\n")
    with pytest.raises(ValueError, match="selects node"):
        load_config(write_yaml("main.yaml", 'n: "~import lib.yaml#b"\n'))


def test_import_missing_file_raises(write_yaml):
    with pytest.raises(FileNotFoundError):
        load_config(write_yaml("main.yaml", "n: ~import missing.yaml\n"))


def test_import_self_raises(write_yaml):
    with pytest.raises(ValueError, match="Circular import"):
        load_config(write_yaml("main.yaml", "n: ~import main.yaml\n"))


def test_import_diamond_is_not_a_cycle(write_yaml):
    write_yaml("leaf.yaml", "v: 1\n")
    write_yaml("left.yaml", "x: ~import leaf.yaml\n")
    write_yaml("right.yaml", "x: ~import leaf.yaml\n")
    cfg = load_config(
        write_yaml("main.yaml", "l: ~import left.yaml\nr: ~import right.yaml\n")
    )
    assert (cfg.l.x.v, cfg.r.x.v) == (1, 1)


def test_import_repeated_file_gives_independent_copies(write_yaml):
    write_yaml("leaf.yaml", "v: 1\n")
    cfg = load_config(
        write_yaml("main.yaml", "a: ~import leaf.yaml\nb: ~import leaf.yaml\n")
    )
    cfg.a.v = 99
    assert cfg.b.v == 1


def test_import_repeated_file_in_list_gives_independent_copies(write_yaml):
    write_yaml("leaf.yaml", "v: 1\n")
    cfg = load_config(
        write_yaml("main.yaml", "l:\n  - ~import leaf.yaml\n  - ~import leaf.yaml\n")
    )
    cfg.l[0].v = 99
    assert cfg.l[1].v == 1


def test_import_repeated_subnode_gives_independent_copies(write_yaml):
    write_yaml("lib.yaml", "a:\n  items: [{v: 1}]\n")
    cfg = load_config(
        write_yaml("main.yaml", 'a: "~import lib.yaml#a"\nb: "~import lib.yaml#a"\n')
    )
    cfg.a["items"][0].v = 99
    assert cfg.b["items"][0].v == 1


def test_import_path_does_not_see_base_keys(write_yaml):
    # contracts §3: an `~import` path sees only keys literally present in its file
    write_yaml("leaf.yaml", "v: 1\n")
    with pytest.raises(InterpolationKeyError):
        load_config(
            write_yaml("main.yaml", "$base: {name: leaf}\nn: ~import ${name}.yaml\n")
        )


def test_import_path_does_not_see_overrides(write_yaml):
    write_yaml("leaf.yaml", "v: 1\n")
    with pytest.raises(InterpolationKeyError):
        load_config(
            write_yaml("main.yaml", "n: ~import ${name}.yaml\n"),
            overrides=["name=leaf"],
        )


def test_import_interpolation_resolves_at_final_position(write_yaml):
    write_yaml("lib.yaml", "own: 1\ncopy: ${.own}\n")
    cfg = load_config(write_yaml("main.yaml", "n: ~import lib.yaml\n"))
    cfg.n.own = 2
    assert OmegaConf.to_container(cfg, resolve=True) == {"n": {"own": 2, "copy": 2}}
