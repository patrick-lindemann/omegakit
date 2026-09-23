from omegakit import load_config

# Contracts: §6 Key namespace.


def test_load_returns_values(write_yaml):
    cfg = load_config(write_yaml("c.yaml", "a: 1\nb: hello\n"))
    assert cfg.a == 1
    assert cfg.b == "hello"


def test_load_keeps_unknown_reserved_keys(write_yaml):
    cfg = load_config(write_yaml("c.yaml", "$foo: 1\n"))
    assert cfg["$foo"] == 1
