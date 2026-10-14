import os
from pathlib import Path

import pytest
from omegaconf import DictConfig, ListConfig, OmegaConf

from omegakit._core.errors import (
    ConfigFileNotFoundError,
    ConfigFilePermissionError,
    ConfigFileSyntaxError,
    OmegaKitBaseException,
)
from omegakit._core.utils.yaml import load_yaml


def test_loads_a_mapping(tmp_path: Path):
    path = tmp_path / "config.yaml"
    path.write_text("model: {hidden: 32}")
    config = load_yaml(path)
    assert isinstance(config, DictConfig)
    assert config.model.hidden == 32


def test_loads_a_list(tmp_path: Path):
    path = tmp_path / "config.yaml"
    path.write_text("[1, 2]")
    config = load_yaml(path)
    assert isinstance(config, ListConfig)
    assert config == [1, 2]


def test_loads_an_empty_file_as_an_empty_mapping(tmp_path: Path):
    path = tmp_path / "config.yaml"
    path.write_text("")
    assert load_yaml(path) == {}


def test_rejects_a_missing_file(tmp_path: Path):
    with pytest.raises(ConfigFileNotFoundError, match=r"nope\.yaml") as error_info:
        load_yaml(tmp_path / "nope.yaml")
    assert error_info.value.filename == str(tmp_path / "nope.yaml")


def test_rejects_a_directory(tmp_path: Path):
    with pytest.raises(ConfigFileNotFoundError):
        load_yaml(tmp_path)


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("a: [1", id="unclosed-list"),
        pytest.param("a: ${", id="malformed-interpolation"),
        pytest.param("a: !!int x", id="invalid-tag-value"),
        pytest.param("42", id="scalar-only"),
    ],
)
def test_rejects_invalid_content(tmp_path: Path, text: str):
    path = tmp_path / "config.yaml"
    path.write_text(text)
    with pytest.raises(ConfigFileSyntaxError, match=r"config\.yaml"):
        load_yaml(path)


def test_rejects_a_file_that_is_not_text(tmp_path: Path):
    path = tmp_path / "config.yaml"
    path.write_bytes(b"a: \xff\xfe")
    with pytest.raises(ConfigFileSyntaxError, match=r"config\.yaml"):
        load_yaml(path)


@pytest.mark.skipif(os.geteuid() == 0, reason="root can read every file")
def test_rejects_an_unreadable_file(tmp_path: Path):
    path = tmp_path / "config.yaml"
    path.write_text("a: 1")
    path.chmod(0)
    with pytest.raises(ConfigFilePermissionError, match=r"config\.yaml") as error_info:
        load_yaml(path)
    assert error_info.value.filename == str(path)


def test_error_of_the_file_system_passes_through(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    path = tmp_path / "config.yaml"
    path.write_text("a: 1")
    monkeypatch.setattr(OmegaConf, "load", _fail_to_read)
    with pytest.raises(OSError, match="Input/output error") as error_info:
        load_yaml(path)
    assert not isinstance(error_info.value, OmegaKitBaseException)


def _fail_to_read(file_path: Path) -> None:
    raise OSError(5, "Input/output error")
