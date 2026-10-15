from pathlib import Path

import pytest

from omegakit._core.utils.path import cast_path, resolve_path


@pytest.mark.parametrize("path", ["configs/model.yaml", Path("configs/model.yaml")])
def test_text_and_path_become_a_path(path: str | Path):
    assert cast_path(path) == Path("configs/model.yaml")


def test_relative_path_is_resolved_against_a_directory(tmp_path: Path):
    assert resolve_path("model.yaml", tmp_path) == (tmp_path / "model.yaml").resolve()
    resolved_path = resolve_path("../model.yaml", str(tmp_path / "configs"))
    assert resolved_path == (tmp_path / "model.yaml").resolve()


def test_absolute_path_ignores_the_directory(tmp_path: Path):
    path = (tmp_path / "model.yaml").resolve()
    assert resolve_path(path, tmp_path / "configs") == path


def test_path_without_a_directory_is_resolved_against_the_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.chdir(tmp_path)
    assert resolve_path("model.yaml") == (tmp_path / "model.yaml").resolve()
