from omegaconf import OmegaConf

from omegakit import load_config

# Contracts: §1 Pipeline order. One test per edge of
# parse → ~import → $base → $defaults → overrides → strip.


def test_pipeline_import_before_base(write_yaml):
    write_yaml("lib.yaml", "a: 1\n")
    cfg = load_config(
        write_yaml("main.yaml", "n:\n  $base: ~import lib.yaml\n  b: 2\n")
    )
    assert dict(cfg.n) == {"a": 1, "b": 2}


def test_pipeline_imported_file_imports_before_its_base(write_yaml):
    write_yaml("leaf.yaml", "a: 1\n")
    write_yaml("mid.yaml", "$base: ~import leaf.yaml\nb: 2\n")
    cfg = load_config(write_yaml("main.yaml", "n: ~import mid.yaml\n"))
    assert dict(cfg.n) == {"a": 1, "b": 2}


def test_pipeline_base_before_defaults(write_yaml):
    write_yaml("lib.yaml", "$defaults: {k: 1}\n")
    cfg = load_config(
        write_yaml(
            "main.yaml",
            "n:\n  $base: ~import lib.yaml\n  x: {}\n  y:\n    $base: {k: 2}\n",
        )
    )
    assert (cfg.n.x.k, cfg.n.y.k) == (1, 2)


def test_pipeline_defaults_before_overrides(write_yaml):
    cfg = load_config(
        write_yaml("main.yaml", "$defaults: {k: 1}\nx: {}\n"), overrides=["x.k=5"]
    )
    assert cfg.x.k == 5


def test_pipeline_overrides_after_assembly(write_yaml):
    cfg = load_config(
        write_yaml("main.yaml", "n: {}\n"),
        overrides={"n": {"$base": {"a": 1}, "$defaults": {"b": 1}}},
    )
    assert set(cfg.n) == {"$base", "$defaults"}


def test_pipeline_strip_after_overrides(write_yaml):
    cfg = load_config(
        write_yaml("main.yaml", "n: {a: 1}\n"),
        overrides={"n": {"$class": "a.B", "$meta": {"x": 1}}},
        keep_targets=False,
    )
    assert OmegaConf.to_container(cfg) == {"n": {"a": 1}}
