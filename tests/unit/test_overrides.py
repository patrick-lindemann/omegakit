from omegakit import load_config


def test_load_applies_list_overrides(write_yaml):
    cfg = load_config(write_yaml("c.yaml", "a: 1\n"), overrides=["a=5"])
    assert cfg.a == 5


def test_load_applies_dict_overrides(write_yaml):
    cfg = load_config(write_yaml("c.yaml", "a: 1\n"), overrides={"a": 5})
    assert cfg.a == 5
