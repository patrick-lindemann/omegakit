import pytest
from omegaconf import OmegaConf
from omegaconf.errors import MissingMandatoryValue

from omegakit import instantiate, load_config
from tests.helpers import (
    POINT,
)


def test_load_top_level_missing_under_base_survives_load(write_yaml):
    write_yaml("lib.yaml", "a: 1\nb: ???\n")
    cfg = load_config(write_yaml("main.yaml", "node:\n  $base: ~import lib.yaml\n"))
    assert cfg.node.a == 1
    with pytest.raises(MissingMandatoryValue):
        _ = cfg.node.b


def test_load_nested_missing_under_base_survives_load(write_yaml):
    write_yaml("lib.yaml", "outer:\n  inner: ???\n")
    cfg = load_config(write_yaml("main.yaml", "node:\n  $base: ~import lib.yaml\n"))
    with pytest.raises(MissingMandatoryValue):
        _ = cfg.node.outer.inner


def test_load_missing_in_list_survives_load(write_yaml):
    cfg = load_config(write_yaml("c.yaml", "items:\n  - ???\n  - 2\n"))
    assert cfg["items"][1] == 2
    with pytest.raises(MissingMandatoryValue):
        _ = cfg["items"][0]


def test_load_filled_missing_via_base(write_yaml):
    write_yaml("lib.yaml", "a: 1\nb: ???\n")
    cfg = load_config(
        write_yaml("main.yaml", "node:\n  $base: ~import lib.yaml\n  b: 5\n")
    )
    assert cfg.node.a == 1
    assert cfg.node.b == 5


def test_load_missing_filled_via_base_resolves_relative_ref(write_yaml):
    # The reusable-library pattern: a file declares a `???` slot and wires its internals
    # to it with a relative interpolation; the consumer fills the slot via `$base`.
    write_yaml("lib.yaml", "manifold: ???\nsde:\n  manifold: ${..manifold}\n")
    cfg = load_config(
        write_yaml(
            "main.yaml",
            "node:\n  $base: ~import lib.yaml\n  manifold: SO3\n",
        )
    )
    assert cfg.node.manifold == "SO3"
    assert cfg.node.sde.manifold == "SO3"


def test_instantiate_raises_on_missing_value():
    # `???` marks a consumer fill-in point; it must fail loudly rather than pass the
    # literal string "???" to the constructor.
    config = OmegaConf.create({"$class": POINT, "x": "???", "y": 2})
    with pytest.raises(MissingMandatoryValue):
        instantiate(config)
