from omegakit import load_config


def test_load_returns_values(write_yaml):
    cfg = load_config(write_yaml("c.yaml", "a: 1\nb: hello\n"))
    assert cfg.a == 1
    assert cfg.b == "hello"
