import pytest
from omegaconf import OmegaConf
from omegaconf.errors import MissingMandatoryValue

from omegakit import instantiate, load_config
from tests.helpers import POINT, RECORDER, Point

# Contracts: §3 Resolution timing, §4 `???` lifecycle, §5 Instantiation.


def test_scenario_defaults_give_every_item_the_same_class(write_yaml):
    """`$defaults` + `$class`: one `$defaults` makes every sibling instantiable."""
    cfg = load_config(
        write_yaml(
            "main.yaml",
            f"points:\n  $defaults: {{$class: {POINT}, y: 0}}\n"
            "  a: {x: 1}\n  b: {x: 2, y: 5}\n",
        )
    )
    points = {key: instantiate(cfg.points[key]) for key in cfg.points}
    assert all(isinstance(point, Point) for point in points.values())
    assert [(p.x, p.y) for p in points.values()] == [(1, 0), (2, 5)]


def test_scenario_imported_base_slot_filled_by_consumer(write_yaml):
    """`~import` + `$base` + `???` + `$class`: the consumer fills a library slot."""
    write_yaml("lib.yaml", f"$class: {POINT}\nx: ???\ny: 2\n")
    cfg = load_config(
        write_yaml("main.yaml", "point:\n  $base: ~import lib.yaml\n  x: 5\n")
    )
    point = instantiate(cfg.point)
    assert (point.x, point.y) == (5, 2)


def test_scenario_missing_filled_by_dotlist_override(write_yaml):
    """`???` + overrides + `$class`: a dotlist override fills a slot before building."""
    path = write_yaml("main.yaml", f"point:\n  $class: {POINT}\n  x: ???\n  y: 2\n")
    assert instantiate(load_config(path, overrides=["point.x=1"]).point).x == 1
    with pytest.raises(MissingMandatoryValue, match=r"point\.x"):
        instantiate(load_config(path).point)


def test_scenario_instantiation_does_not_mutate_loaded_config(write_yaml):
    """Loaded config + `instantiate` with overrides: the input stays untouched."""
    cfg = load_config(
        write_yaml(
            "main.yaml", f"point:\n  $class: {POINT}\n  x: ${{z}}\n  y: 1\nz: 2\n"
        )
    )
    before = OmegaConf.to_yaml(cfg)
    point = instantiate(cfg.point, overrides={"y": 3})
    assert (point.x, point.y) == (2, 3)
    instantiate(cfg.point)
    assert OmegaConf.to_yaml(cfg) == before


def test_scenario_golden_reusable_library(write_yaml):
    """Golden case: a library with `???` slots wired by relative interpolations."""
    write_yaml(
        "sde.yaml",
        "manifold: ???\n"
        "steps: 100\n"
        "sde:\n"
        f"  $class: {RECORDER}\n"
        "  manifold: ${..manifold}\n"
        "  steps: ${..steps}\n",
    )
    cfg = load_config(
        write_yaml(
            "main.yaml",
            "model:\n  $base: ~import sde.yaml\n  manifold: SO3\n",
        )
    )
    config, _ = instantiate(cfg.model.sde)
    assert config == {"manifold": "SO3", "steps": 100}


def test_scenario_golden_dataset_manifest(write_yaml):
    """Golden case: a dataset manifest whose items share `$defaults`."""
    cfg = load_config(
        write_yaml(
            "main.yaml",
            "root: /data\n"
            "records:\n"
            "  $defaults:\n"
            f"    $class: {RECORDER}\n"
            "    path: ${root}/${.id}.h5\n"
            "    scale: 1.0\n"
            "  sphere: {id: sphere}\n"
            "  cube: {id: cube, scale: 2.0}\n",
        )
    )
    records = [instantiate(cfg.records[key])[0] for key in cfg.records]
    assert records == [
        {"id": "sphere", "path": "/data/sphere.h5", "scale": 1.0},
        {"id": "cube", "path": "/data/cube.h5", "scale": 2.0},
    ]
