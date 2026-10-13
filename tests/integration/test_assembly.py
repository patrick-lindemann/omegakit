import datetime
from pathlib import Path

from omegaconf import DictConfig

from omegakit._core.file import load_yaml
from omegakit._features.base import merge_bases
from omegakit._features.defaults import apply_defaults
from omegakit._features.import_ import resolve_imports
from omegakit._features.meta import remove_meta
from omegakit._features.overrides import apply_overrides
from omegakit.instantiate import instantiate


def test_overrides_win_over_imported_values(tmp_path: Path):
    (tmp_path / "configs").mkdir()
    (tmp_path / "configs/optimizer.yaml").write_text(
        "sgd: {$meta: {description: Plain SGD}, lr: '${lr}', momentum: 0.9}"
    )
    (tmp_path / "configs/model.yaml").write_text(
        "$meta: {description: The baseline MLP}\n"
        "hidden: 32\n"
        'optimizer: "~import optimizer.yaml#sgd"\n'
    )
    experiment_path = tmp_path / "experiment.yaml"
    experiment_path.write_text(
        "$meta: {title: Wide MLP}\nlr: 0.1\nmodel: ~import configs/model.yaml\n"
    )
    config = load_yaml(experiment_path)
    assert isinstance(config, DictConfig)
    config = resolve_imports(config, experiment_path)
    config = apply_overrides(config, ["model.hidden=256", "lr=0.01"])
    config = remove_meta(config)
    assert config == {
        "lr": 0.01,
        "model": {"hidden": 256, "optimizer": {"lr": 0.01, "momentum": 0.9}},
    }


def test_imported_base_and_defaults_are_assembled_before_overrides(tmp_path: Path):
    (tmp_path / "base.yaml").write_text(
        "epochs: 200\n"
        "data:\n"
        "  $defaults: {n: 256, noise: 0.1}\n"
        "  train: {seed: 0}\n"
        "  test: {$base: '${..train}', seed: 1234}\n"
    )
    experiment_path = tmp_path / "experiment.yaml"
    experiment_path.write_text(
        "$base: ~import base.yaml\ndata:\n  validation: {n: 64}\n"
    )
    config = load_yaml(experiment_path)
    assert isinstance(config, DictConfig)
    config = resolve_imports(config, experiment_path)
    config = merge_bases(config)
    config = apply_defaults(config)
    config = apply_overrides(config, ["data.train.seed=7", "epochs=1"])
    assert config == {
        "epochs": 1,
        "data": {
            "train": {"n": 256, "noise": 0.1, "seed": 7},
            "test": {"n": 256, "noise": 0.1, "seed": 1234},
            "validation": {"n": 64, "noise": 0.1},
        },
    }


def test_assembled_config_is_instantiated(tmp_path: Path):
    (tmp_path / "limits.yaml").write_text(
        "$defaults: {$class: datetime.timedelta, seconds: 30}\n"
        "short: {}\n"
        "long: {hours: '${hours}'}\n"
    )
    experiment_path = tmp_path / "experiment.yaml"
    experiment_path.write_text(
        "$class: builtins.dict\n"
        "$meta: {title: Timeouts}\n"
        "hours: 1\n"
        "limits: ~import limits.yaml\n"
        "clock: {$ref: datetime.datetime}\n"
    )
    config = load_yaml(experiment_path)
    assert isinstance(config, DictConfig)
    config = resolve_imports(config, experiment_path)
    config = merge_bases(config)
    config = apply_defaults(config)
    config = apply_overrides(config, ["hours=2"])
    experiment = instantiate(config)
    assert experiment == {
        "hours": 2,
        "limits": {
            "short": datetime.timedelta(seconds=30),
            "long": datetime.timedelta(hours=2, seconds=30),
        },
        "clock": datetime.datetime,
    }
