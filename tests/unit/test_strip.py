from omegakit import load_config

# Contracts: §1 Pipeline order.


def test_load_drops_meta_by_default(write_yaml):
    cfg = load_config(write_yaml("c.yaml", "$meta:\n  author: x\na: 1\n"))
    assert "$meta" not in cfg
    assert cfg.a == 1


def test_load_keeps_meta_when_requested(write_yaml):
    cfg = load_config(
        write_yaml("c.yaml", "$meta:\n  author: x\na: 1\n"), keep_meta=True
    )
    assert cfg["$meta"]["author"] == "x"


def test_load_keeps_targets_by_default(write_yaml):
    cfg = load_config(write_yaml("c.yaml", "$class: some.Thing\na: 1\n"))
    assert cfg["$class"] == "some.Thing"


def test_load_drops_targets_when_disabled(write_yaml):
    cfg = load_config(
        write_yaml("c.yaml", "$class: some.Thing\na: 1\n"),
        keep_targets=False,
    )
    assert "$class" not in cfg
    assert cfg.a == 1


def test_load_drops_nested_meta(write_yaml):
    cfg = load_config(write_yaml("c.yaml", "outer:\n  $meta:\n    a: 1\n  b: 2\n"))
    assert "$meta" not in cfg.outer
    assert cfg.outer.b == 2


def test_load_drops_nested_targets_when_disabled(write_yaml):
    cfg = load_config(
        write_yaml("c.yaml", "outer:\n  $class: foo.Bar\n  b: 2\n"),
        keep_targets=False,
    )
    assert "$class" not in cfg.outer
    assert cfg.outer.b == 2


def test_strip_keys_in_nested_lists(write_yaml):
    cfg = load_config(
        write_yaml("c.yaml", "nested: [[{$meta: secret, $class: some.Type, x: 1}]]"),
        keep_targets=False,
    )
    assert dict(cfg.nested[0][0]) == {"x": 1}


def test_strip_all_targets_when_disabled(write_yaml):
    cfg = load_config(
        write_yaml(
            "c.yaml", "n:\n  $class: a.B\n  $partial: true\n  x:\n    $ref: a.C\n"
        ),
        keep_targets=False,
    )
    assert dict(cfg.n) == {"x": {}}


def test_strip_meta_introduced_by_overrides(write_yaml):
    cfg = load_config(
        write_yaml("c.yaml", "n: {a: 1}\n"), overrides={"n": {"$meta": {"x": 1}}}
    )
    assert "$meta" not in cfg.n


def test_strip_meta_and_targets_together(write_yaml):
    cfg = load_config(
        write_yaml("c.yaml", "$meta: {x: 1}\n$class: a.B\nv: 1\n"),
        keep_targets=False,
    )
    assert dict(cfg) == {"v": 1}
