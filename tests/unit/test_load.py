import pytest
import yaml

from omegakit import ConfigValidationError, load_config

# Contracts: §6 Key namespace.


def test_load_returns_values(write_yaml):
    cfg = load_config(write_yaml("c.yaml", "a: 1\nb: hello\n"))
    assert cfg.a == 1
    assert cfg.b == "hello"


def test_load_keeps_unknown_reserved_keys(write_yaml):
    cfg = load_config(write_yaml("c.yaml", "$foo: 1\n"))
    assert cfg["$foo"] == 1


@pytest.mark.parametrize(
    ("text", "match"),
    [
        ("a: [1\n", "while parsing"),
        ("a: 1\na: 2\n", "duplicate key"),
        ("a: !nope 1\n", "tag '!nope'"),
    ],
)
def test_load_rejects_invalid_yaml(write_yaml, text, match):
    path = write_yaml("c.yaml", text)
    with pytest.raises(ConfigValidationError, match=match) as info:
        load_config(path)
    assert str(path) in str(info.value)
    assert isinstance(info.value.__cause__, yaml.YAMLError)


def test_load_rejects_a_file_that_is_not_utf8(tmp_path):
    path = tmp_path / "c.yaml"
    path.write_bytes(b"a: \xff\n")
    with pytest.raises(ConfigValidationError, match="utf-8") as info:
        load_config(path)
    assert isinstance(info.value.__cause__, UnicodeDecodeError)


def test_load_missing_root_file_raises_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "missing.yaml")
