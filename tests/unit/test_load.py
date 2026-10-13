from pathlib import Path

import pytest

from omegakit._core.file import ConfigFileNotFoundError
from omegakit._features.include import IncludeRootError
from omegakit.load import LoadTypeError, load_config


def test_loads_the_values_of_a_file(tmp_path: Path):
    path = tmp_path / "config.yaml"
    path.write_text("seed: 1\nmodel: {hidden: 32}")
    assert load_config(path) == {"seed": 1, "model": {"hidden": 32}}
    assert load_config(str(path)) == {"seed": 1, "model": {"hidden": 32}}


def test_assembles_includes_bases_and_each(tmp_path: Path):
    (tmp_path / "base.yaml").write_text(
        "epochs: 200\n"
        "data:\n"
        "  $each: {n: 256}\n"
        "  train: {seed: 0}\n"
        "  test: {$base: '${..train}', seed: 1}\n"
    )
    path = tmp_path / "experiment.yaml"
    path.write_text("$base: ~include base.yaml\nepochs: 5\n")
    assert load_config(path) == {
        "epochs": 5,
        "data": {"train": {"n": 256, "seed": 0}, "test": {"n": 256, "seed": 1}},
    }


@pytest.mark.parametrize("overrides", [["model.hidden=64", "seed=2"], {"seed": 2}])
def test_overrides_win_over_the_file(tmp_path: Path, overrides: list | dict):
    (tmp_path / "model.yaml").write_text("hidden: 32")
    path = tmp_path / "config.yaml"
    path.write_text("seed: 1\nmodel: ~include model.yaml")
    config = load_config(path, overrides)
    assert config.seed == 2
    assert config.model.hidden == (64 if isinstance(overrides, list) else 32)


def test_meta_is_removed_unless_kept(tmp_path: Path):
    path = tmp_path / "config.yaml"
    path.write_text("$meta: {title: Baseline}\nmodel: {$meta: note, hidden: 32}")
    assert load_config(path) == {"model": {"hidden": 32}}
    assert load_config(path, keep_meta=True) == {
        "$meta": {"title": "Baseline"},
        "model": {"$meta": "note", "hidden": 32},
    }


def test_targets_are_kept(tmp_path: Path):
    path = tmp_path / "config.yaml"
    path.write_text("half: {$target: fractions.Fraction, $args: [1, 2]}")
    assert load_config(path) == {
        "half": {"$target": "fractions.Fraction", "$args": [1, 2]}
    }


def test_include_outside_the_include_root_is_rejected(tmp_path: Path):
    (tmp_path / "configs").mkdir()
    (tmp_path / "model.yaml").write_text("hidden: 32")
    path = tmp_path / "configs/config.yaml"
    path.write_text("model: ~include ../model.yaml")
    assert load_config(path, include_root=tmp_path) == {"model": {"hidden": 32}}
    with pytest.raises(IncludeRootError):
        load_config(path, include_root=tmp_path / "configs")


def test_missing_file_is_rejected(tmp_path: Path):
    with pytest.raises(ConfigFileNotFoundError):
        load_config(tmp_path / "missing.yaml")


def test_list_at_the_root_is_rejected(tmp_path: Path):
    path = tmp_path / "config.yaml"
    path.write_text("- a\n- b\n")
    with pytest.raises(LoadTypeError, match="root is a list"):
        load_config(path)
    assert issubclass(LoadTypeError, TypeError)
