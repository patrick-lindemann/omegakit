import pytest
from omegaconf import OmegaConf

from omegakit import load_config

# Contracts: §1 Pipeline order, §2 Precedence, §8 Error model.


def test_load_applies_list_overrides(write_yaml):
    cfg = load_config(write_yaml("c.yaml", "a: 1\n"), overrides=["a=5"])
    assert cfg.a == 5


def test_load_applies_dict_overrides(write_yaml):
    cfg = load_config(write_yaml("c.yaml", "a: 1\n"), overrides={"a": 5})
    assert cfg.a == 5


def test_overrides_accept_dict_config(write_yaml):
    cfg = load_config(
        write_yaml("c.yaml", "a: 1\n"), overrides=OmegaConf.create({"a": 5})
    )
    assert cfg.a == 5


@pytest.mark.parametrize("overrides", [5, ("a=2",), "a=2"])
def test_overrides_invalid_type_raises(write_yaml, overrides):
    with pytest.raises(ValueError, match="Unsupported overrides type"):
        load_config(write_yaml("c.yaml", "a: 1\n"), overrides=overrides)


def test_overrides_win_over_base(write_yaml):
    cfg = load_config(
        write_yaml("c.yaml", "n:\n  $base: {a: 1}\n  a: 2\n"), overrides=["n.a=9"]
    )
    assert cfg.n.a == 9


def test_overrides_do_not_rerun_assembly(write_yaml):
    write_yaml("leaf.yaml", "v: 1\n")
    cfg = load_config(
        write_yaml("c.yaml", "n: {}\n"),
        overrides={
            "n": {
                "i": "~import leaf.yaml",
                "$base": {"q": 1},
                "$defaults": {"z": 1},
                "s": {},
            }
        },
    )
    assert cfg.n.i == "~import leaf.yaml"
    assert cfg.n["$base"] == {"q": 1}
    assert cfg.n["$defaults"] == {"z": 1}
    assert dict(cfg.n.s) == {}


def test_overrides_seen_by_lazy_interpolation(write_yaml):
    cfg = load_config(write_yaml("c.yaml", "a: 1\nb: ${a}\n"), overrides=["a=5"])
    assert cfg.b == 5
