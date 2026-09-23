from pathlib import Path

import pytest
from omegaconf.errors import InterpolationResolutionError, MissingMandatoryValue

from omegakit import load_config
from omegakit.resolvers.paths import register_paths_resolver
from tests.helpers import write_text


def test_load_returns_values(tmp_path: Path):
    cfg = load_config(write_text(tmp_path / "c.yaml", "a: 1\nb: hello\n"))
    assert cfg.a == 1
    assert cfg.b == "hello"


def test_load_applies_list_overrides(tmp_path: Path):
    cfg = load_config(write_text(tmp_path / "c.yaml", "a: 1\n"), overrides=["a=5"])
    assert cfg.a == 5


def test_load_applies_dict_overrides(tmp_path: Path):
    cfg = load_config(write_text(tmp_path / "c.yaml", "a: 1\n"), overrides={"a": 5})
    assert cfg.a == 5


def test_load_drops_meta_by_default(tmp_path: Path):
    cfg = load_config(write_text(tmp_path / "c.yaml", "$meta:\n  author: x\na: 1\n"))
    assert "$meta" not in cfg
    assert cfg.a == 1


def test_load_keeps_meta_when_requested(tmp_path: Path):
    cfg = load_config(
        write_text(tmp_path / "c.yaml", "$meta:\n  author: x\na: 1\n"), keep_meta=True
    )
    assert cfg["$meta"]["author"] == "x"


def test_load_keeps_targets_by_default(tmp_path: Path):
    cfg = load_config(write_text(tmp_path / "c.yaml", "$class: some.Thing\na: 1\n"))
    assert cfg["$class"] == "some.Thing"


def test_load_drops_targets_when_disabled(tmp_path: Path):
    cfg = load_config(
        write_text(tmp_path / "c.yaml", "$class: some.Thing\na: 1\n"),
        keep_targets=False,
    )
    assert "$class" not in cfg
    assert cfg.a == 1


def test_load_merges_base_with_node_winning(tmp_path: Path):
    cfg = load_config(
        write_text(tmp_path / "c.yaml", "$base:\n  a: 1\n  b: 2\nb: 20\n")
    )
    assert cfg.a == 1
    assert cfg.b == 20


def test_load_resolves_import(tmp_path: Path):
    write_text(tmp_path / "base.yaml", "x: 10\n")
    cfg = load_config(write_text(tmp_path / "main.yaml", "foo: ~import base.yaml\n"))
    assert cfg.foo.x == 10


def test_load_circular_import_raises(tmp_path: Path):
    write_text(tmp_path / "a.yaml", "foo: ~import b.yaml\n")
    write_text(tmp_path / "b.yaml", "bar: ~import a.yaml\n")
    with pytest.raises(ValueError, match="Circular import"):
        load_config(tmp_path / "a.yaml")


def test_load_resolves_paths(tmp_path: Path):
    register_paths_resolver({"root_dir": tmp_path})
    cfg = load_config(write_text(tmp_path / "c.yaml", "p: ${paths:root_dir}\n"))
    assert cfg.p == str(tmp_path)


def test_load_import_selects_subnode(tmp_path: Path):
    write_text(tmp_path / "base.yaml", "opt:\n  lr: 5\nother: 2\n")
    cfg = load_config(
        write_text(tmp_path / "main.yaml", 'foo: "~import base.yaml#opt"\n')
    )
    assert cfg.foo.lr == 5
    assert "other" not in cfg.foo


def test_load_resolves_import_in_list(tmp_path: Path):
    write_text(tmp_path / "leaf.yaml", "v: 42\n")
    cfg = load_config(
        write_text(tmp_path / "main.yaml", "nodes:\n  - ~import leaf.yaml\n  - other\n")
    )
    assert cfg.nodes[0].v == 42
    assert cfg.nodes[1] == "other"


def test_load_resolves_base_import_in_list_item(tmp_path: Path):
    # The `stages:` pattern: a list item merges an imported `$base` under its own keys.
    write_text(tmp_path / "defaults.yaml", "lr: 5\nsteps: 100\n")
    cfg = load_config(
        write_text(
            tmp_path / "main.yaml",
            "stages:\n  - $base: ~import defaults.yaml\n    steps: 3\n",
        )
    )
    assert cfg.stages[0].lr == 5
    assert cfg.stages[0].steps == 3


def test_load_import_selects_subnode_in_list(tmp_path: Path):
    write_text(tmp_path / "base.yaml", "opt:\n  lr: 5\nother: 2\n")
    cfg = load_config(
        write_text(tmp_path / "main.yaml", 'nodes:\n  - "~import base.yaml#opt"\n')
    )
    assert cfg.nodes[0].lr == 5
    assert "other" not in cfg.nodes[0]


def test_load_resolves_nested_imports(tmp_path: Path):
    write_text(tmp_path / "leaf.yaml", "v: 42\n")
    write_text(tmp_path / "mid.yaml", "x: ~import leaf.yaml\n")
    cfg = load_config(write_text(tmp_path / "main.yaml", "y: ~import mid.yaml\n"))
    assert cfg.y.x.v == 42


def test_load_import_absolute_path(tmp_path: Path):
    leaf = write_text(tmp_path / "leaf.yaml", "v: 42\n")
    (tmp_path / "sub").mkdir()
    cfg = load_config(
        write_text(tmp_path / "sub" / "main.yaml", f"foo: ~import {leaf}\n")
    )
    assert cfg.foo.v == 42


def test_load_import_resolves_config_interpolation(tmp_path: Path):
    write_text(tmp_path / "leaf.yaml", "v: 42\n")
    cfg = load_config(
        write_text(
            tmp_path / "main.yaml",
            f"base_dir: {tmp_path}\nfoo: ~import ${{base_dir}}/leaf.yaml\n",
        )
    )
    assert cfg.foo.v == 42


def test_load_import_resolves_resolver_interpolation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("GRASPDIFF_TEST_IMPORT_DIR", str(tmp_path))
    write_text(tmp_path / "leaf.yaml", "v: 42\n")
    cfg = load_config(
        write_text(
            tmp_path / "main.yaml",
            "foo: ~import ${oc.env:GRASPDIFF_TEST_IMPORT_DIR}/leaf.yaml\n",
        )
    )
    assert cfg.foo.v == 42


def test_load_import_resolves_relative_interpolation(tmp_path: Path):
    (tmp_path / "sub").mkdir()
    write_text(tmp_path / "sub" / "leaf.yaml", "v: 42\n")
    cfg = load_config(
        write_text(
            tmp_path / "main.yaml",
            "node:\n  dir: sub\n  foo: ~import ${.dir}/leaf.yaml\n",
        )
    )
    assert cfg.node.foo.v == 42


def test_load_import_resolves_interpolation_in_list(tmp_path: Path):
    write_text(tmp_path / "leaf.yaml", "v: 42\n")
    cfg = load_config(
        write_text(
            tmp_path / "main.yaml",
            f"base_dir: {tmp_path}\nnodes:\n  - ~import ${{base_dir}}/leaf.yaml\n",
        )
    )
    assert cfg.nodes[0].v == 42


def test_load_import_unresolvable_interpolation_raises(tmp_path: Path):
    with pytest.raises(InterpolationResolutionError):
        load_config(
            write_text(tmp_path / "main.yaml", "foo: ~import ${missing}/leaf.yaml\n")
        )


def test_load_import_resolves_relative_to_importer(tmp_path: Path):
    (tmp_path / "sub").mkdir()
    write_text(tmp_path / "sub" / "leaf.yaml", "v: 7\n")
    write_text(tmp_path / "sub" / "mid.yaml", "bar: ~import leaf.yaml\n")
    cfg = load_config(write_text(tmp_path / "main.yaml", "foo: ~import sub/mid.yaml\n"))
    # `leaf.yaml` must resolve relative to sub/ (the importer), not the top dir.
    assert cfg.foo.bar.v == 7


def test_load_merges_nested_base(tmp_path: Path):
    cfg = load_config(
        write_text(
            tmp_path / "c.yaml",
            "model:\n  $base:\n    lr: 5\n    steps: 100\n  steps: 3\n",
        )
    )
    assert cfg.model.lr == 5
    assert cfg.model.steps == 3


def test_load_base_populated_by_import(tmp_path: Path):
    write_text(tmp_path / "defaults.yaml", "lr: 5\nsteps: 100\n")
    cfg = load_config(
        write_text(
            tmp_path / "main.yaml",
            "model:\n  $base: ~import defaults.yaml\n  steps: 3\n",
        )
    )
    # Imports resolve before base merging, so `$base: ~import ...` becomes a dict first.
    assert cfg.model.lr == 5
    assert cfg.model.steps == 3


def test_load_base_non_dict_raises(tmp_path: Path):
    with pytest.raises(ValueError, match="is not a dictionary or a list"):
        load_config(write_text(tmp_path / "c.yaml", "$base: 5\na: 1\n"))


def test_load_merges_list_base_with_later_winning(tmp_path: Path):
    # A list `$base` merges its elements left to right; later elements win, and the
    # node's own keys win over all of them.
    cfg = load_config(
        write_text(
            tmp_path / "c.yaml",
            "$base:\n  - { a: 1, b: 1, c: 1 }\n  - { b: 2, c: 2 }\nc: 3\n",
        )
    )
    assert (cfg.a, cfg.b, cfg.c) == (1, 2, 3)


def test_load_merges_list_base_from_imports(tmp_path: Path):
    write_text(tmp_path / "globals.yaml", "seed: 42\nprecision: high\n")
    write_text(tmp_path / "model.yaml", "model:\n  lr: 5\n")
    cfg = load_config(
        write_text(
            tmp_path / "main.yaml",
            "$base:\n  - ~import globals.yaml\n  - ~import model.yaml\nseed: 7\n",
        )
    )
    assert cfg.seed == 7
    assert cfg.precision == "high"
    assert cfg.model.lr == 5


def test_load_list_base_non_dict_element_raises(tmp_path: Path):
    with pytest.raises(ValueError, match="must contain only dictionaries"):
        load_config(write_text(tmp_path / "c.yaml", "$base:\n  - { a: 1 }\n  - 5\n"))


def test_load_drops_nested_meta(tmp_path: Path):
    cfg = load_config(
        write_text(tmp_path / "c.yaml", "outer:\n  $meta:\n    a: 1\n  b: 2\n")
    )
    assert "$meta" not in cfg.outer
    assert cfg.outer.b == 2


def test_load_drops_nested_targets_when_disabled(tmp_path: Path):
    cfg = load_config(
        write_text(tmp_path / "c.yaml", "outer:\n  $class: foo.Bar\n  b: 2\n"),
        keep_targets=False,
    )
    assert "$class" not in cfg.outer
    assert cfg.outer.b == 2


# Resolution contract: assembly (`~import` + `$base`) is structural and resolves nothing
# but the reference itself; every `${...}` and `???` is carried through, resolved once
# later, uniformly regardless of nesting depth or import shape.


def test_load_leaf_import_resolves_against_root(tmp_path: Path):
    # An imported leaf interpolation resolves against the CONSUMER root, like a
    # container import — not against the imported file's own scope.
    write_text(tmp_path / "base.yaml", "p: base_p\nq: ${p}\n")
    cfg = load_config(
        write_text(tmp_path / "main.yaml", 'leaf: "~import base.yaml#q"\np: root_p\n')
    )
    assert cfg.leaf == "root_p"


def test_load_top_level_missing_under_base_survives_load(tmp_path: Path):
    write_text(tmp_path / "lib.yaml", "a: 1\nb: ???\n")
    cfg = load_config(
        write_text(tmp_path / "main.yaml", "node:\n  $base: ~import lib.yaml\n")
    )
    assert cfg.node.a == 1
    with pytest.raises(MissingMandatoryValue):
        _ = cfg.node.b


def test_load_nested_missing_under_base_survives_load(tmp_path: Path):
    write_text(tmp_path / "lib.yaml", "outer:\n  inner: ???\n")
    cfg = load_config(
        write_text(tmp_path / "main.yaml", "node:\n  $base: ~import lib.yaml\n")
    )
    with pytest.raises(MissingMandatoryValue):
        _ = cfg.node.outer.inner


def test_load_missing_in_list_survives_load(tmp_path: Path):
    cfg = load_config(write_text(tmp_path / "c.yaml", "items:\n  - ???\n  - 2\n"))
    assert cfg["items"][1] == 2
    with pytest.raises(MissingMandatoryValue):
        _ = cfg["items"][0]


def test_load_filled_missing_via_base(tmp_path: Path):
    write_text(tmp_path / "lib.yaml", "a: 1\nb: ???\n")
    cfg = load_config(
        write_text(tmp_path / "main.yaml", "node:\n  $base: ~import lib.yaml\n  b: 5\n")
    )
    assert cfg.node.a == 1
    assert cfg.node.b == 5


def test_load_top_level_interpolation_under_base_is_lazy(tmp_path: Path):
    # A top-level `${...}` under a `$base` node must resolve lazily against the final
    # tree, not be baked at load time.
    write_text(tmp_path / "lib.yaml", "a: 1\nb: ???\n")
    cfg = load_config(
        write_text(
            tmp_path / "main.yaml",
            "target: from_root\nnode:\n  $base: ~import lib.yaml\n  b: ${target}\n",
        )
    )
    assert cfg.node.b == "from_root"
    cfg.target = "changed"
    assert cfg.node.b == "changed"


def test_load_merges_defaults_into_dict_siblings(tmp_path: Path):
    cfg = load_config(
        write_text(
            tmp_path / "c.yaml",
            "node:\n  $defaults:\n    p: 1\n  a: {q: 2}\n  b: {q: 3}\n",
        )
    )
    assert (cfg.node.a.p, cfg.node.a.q) == (1, 2)
    assert (cfg.node.b.p, cfg.node.b.q) == (1, 3)


def test_load_defaults_skips_scalar_and_list_siblings(tmp_path: Path):
    cfg = load_config(
        write_text(
            tmp_path / "c.yaml",
            "node:\n  $defaults:\n    p: 1\n  s: 5\n  l:\n    - {q: 2}\n  d: {}\n",
        )
    )
    assert cfg.node.s == 5
    assert "p" not in cfg.node.l[0]
    assert cfg.node.d.p == 1


def test_load_defaults_item_keys_win(tmp_path: Path):
    cfg = load_config(
        write_text(tmp_path / "c.yaml", "node:\n  $defaults:\n    p: 1\n  a: {p: 2}\n")
    )
    assert cfg.node.a.p == 2


def test_load_defaults_skips_special_keys(tmp_path: Path):
    cfg = load_config(
        write_text(
            tmp_path / "c.yaml",
            "node:\n  $defaults:\n    p: 1\n  $meta:\n    author: x\n  a: {}\n",
        ),
        keep_meta=True,
    )
    assert "p" not in cfg.node["$meta"]
    assert cfg.node.a.p == 1


def test_load_defaults_non_dict_raises(tmp_path: Path):
    with pytest.raises(ValueError, match="is not a dictionary"):
        load_config(write_text(tmp_path / "c.yaml", "node:\n  $defaults: 5\n  a: {}\n"))


def test_load_nested_defaults_inner_wins(tmp_path: Path):
    cfg = load_config(
        write_text(
            tmp_path / "c.yaml",
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


def test_load_defaults_deep_merge(tmp_path: Path):
    cfg = load_config(
        write_text(
            tmp_path / "c.yaml",
            "node:\n  $defaults:\n    opts: {a: 1, b: 2}\n  item:\n    opts: {b: 3}\n",
        )
    )
    assert (cfg.node.item.opts.a, cfg.node.item.opts.b) == (1, 3)


def test_load_defaults_populated_by_base_import(tmp_path: Path):
    write_text(tmp_path / "lib.yaml", "$defaults:\n  p: 1\n")
    cfg = load_config(
        write_text(
            tmp_path / "main.yaml",
            "node:\n  $base: ~import lib.yaml\n  item: {q: 2}\n",
        )
    )
    assert (cfg.node.item.p, cfg.node.item.q) == (1, 2)


def test_load_base_inside_defaults_assembled_before_distribution(tmp_path: Path):
    cfg = load_config(
        write_text(
            tmp_path / "c.yaml",
            "node:\n  $defaults:\n    $base: {a: 1}\n    b: 2\n  item: {c: 3}\n",
        )
    )
    assert (cfg.node.item.a, cfg.node.item.b, cfg.node.item.c) == (1, 2, 3)


def test_load_defaults_sibling_base_resolved_first(tmp_path: Path):
    cfg = load_config(
        write_text(
            tmp_path / "c.yaml",
            "node:\n  $defaults: {d: 1}\n  item:\n    $base: {x: 5}\n    y: 2\n",
        )
    )
    assert (cfg.node.item.x, cfg.node.item.y, cfg.node.item.d) == (5, 2, 1)


def test_load_defaults_relative_interpolation_resolves(tmp_path: Path):
    cfg = load_config(
        write_text(
            tmp_path / "c.yaml",
            "records:\n"
            "  $defaults:\n"
            "    path: prefix/${.id}.h5\n"
            "  sphere: {id: sphere}\n"
            "  cube: {id: cube}\n",
        )
    )
    assert cfg.records.sphere.path == "prefix/sphere.h5"
    assert cfg.records.cube.path == "prefix/cube.h5"


def test_load_defaults_absolute_interpolation_resolves_from_root(tmp_path: Path):
    cfg = load_config(
        write_text(
            tmp_path / "c.yaml",
            "base_dir: /data\n"
            "records:\n"
            "  $defaults:\n"
            "    path: ${base_dir}/${.id}.h5\n"
            "  sphere: {id: sphere}\n",
        )
    )
    assert cfg.records.sphere.path == "/data/sphere.h5"


def test_load_defaults_dropped_from_output(tmp_path: Path):
    cfg = load_config(
        write_text(tmp_path / "c.yaml", "node:\n  $defaults: {p: 1}\n  a: {}\n")
    )
    assert "$defaults" not in cfg.node


def test_load_missing_filled_via_base_resolves_relative_ref(tmp_path: Path):
    # The reusable-library pattern: a file declares a `???` slot and wires its internals
    # to it with a relative interpolation; the consumer fills the slot via `$base`.
    write_text(
        tmp_path / "lib.yaml", "manifold: ???\nsde:\n  manifold: ${..manifold}\n"
    )
    cfg = load_config(
        write_text(
            tmp_path / "main.yaml",
            "node:\n  $base: ~import lib.yaml\n  manifold: SO3\n",
        )
    )
    assert cfg.node.manifold == "SO3"
    assert cfg.node.sde.manifold == "SO3"


def test_strip_keys_in_nested_lists(tmp_path):
    cfg = load_config(
        write_text(
            tmp_path / "c.yaml", "nested: [[{$meta: secret, $class: some.Type, x: 1}]]"
        ),
        keep_targets=False,
    )
    assert dict(cfg.nested[0][0]) == {"x": 1}
