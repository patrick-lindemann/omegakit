import pytest
import yaml

from omegakit import ConfigLoadError, load_config


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
    with pytest.raises(ConfigLoadError, match=match) as info:
        load_config(path)
    assert str(path) in str(info.value)
    assert isinstance(info.value.__cause__, yaml.YAMLError)


def test_load_rejects_a_file_that_is_not_utf8(tmp_path):
    path = tmp_path / "c.yaml"
    path.write_bytes(b"a: \xff\n")
    with pytest.raises(ConfigLoadError, match="utf-8") as info:
        load_config(path)
    assert isinstance(info.value.__cause__, UnicodeDecodeError)


def test_load_missing_root_file_raises_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "missing.yaml")


@pytest.mark.parametrize("text", ["hello\n", "5\n", '"a: 1"\n'])
def test_load_rejects_a_file_with_a_single_value(write_yaml, text):
    with pytest.raises(ConfigLoadError, match="single value"):
        load_config(write_yaml("c.yaml", text))


@pytest.mark.parametrize("text", ["", "null\n", "~\n", "---\n"])
def test_load_empty_files_are_empty_mappings(write_yaml, text):
    assert load_config(write_yaml("c.yaml", text)) == {}


def test_load_rejects_a_list_at_the_root(write_yaml):
    with pytest.raises(ConfigLoadError, match="root is a list"):
        load_config(write_yaml("c.yaml", "- a\n- b\n"))


def test_load_imports_a_file_whose_root_is_a_list(write_yaml):
    write_yaml("items.yaml", "- a\n- b\n")
    cfg = load_config(write_yaml("c.yaml", "items: ~import items.yaml\n"))
    assert list(cfg["items"]) == ["a", "b"]
