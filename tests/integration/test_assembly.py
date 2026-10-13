import datetime
from pathlib import Path

from omegakit._core.instantiate import instantiate
from omegakit._core.load import load_config


def test_overrides_win_over_included_values(tmp_path: Path):
    (tmp_path / "configs").mkdir()
    (tmp_path / "configs/optimizer.yaml").write_text(
        "sgd: {$meta: {description: Plain SGD}, lr: '${lr}', momentum: 0.9}"
    )
    (tmp_path / "configs/model.yaml").write_text(
        "$meta: {description: The baseline MLP}\n"
        "hidden: 32\n"
        'optimizer: "~include optimizer.yaml#sgd"\n'
    )
    experiment_path = tmp_path / "experiment.yaml"
    experiment_path.write_text(
        "$meta: {title: Wide MLP}\nlr: 0.1\nmodel: ~include configs/model.yaml\n"
    )
    config = load_config(experiment_path, ["model.hidden=256", "lr=0.01"])
    assert config == {
        "lr": 0.01,
        "model": {"hidden": 256, "optimizer": {"lr": 0.01, "momentum": 0.9}},
    }


def test_included_base_and_each_are_assembled_before_overrides(tmp_path: Path):
    (tmp_path / "base.yaml").write_text(
        "epochs: 200\n"
        "data:\n"
        "  $each: {n: 256, noise: 0.1}\n"
        "  train: {seed: 0}\n"
        "  test: {$base: '${..train}', seed: 1234}\n"
    )
    experiment_path = tmp_path / "experiment.yaml"
    experiment_path.write_text(
        "$base: ~include base.yaml\ndata:\n  validation: {n: 64}\n"
    )
    config = load_config(experiment_path, ["data.train.seed=7", "epochs=1"])
    assert config == {
        "epochs": 1,
        "data": {
            "train": {"n": 256, "noise": 0.1, "seed": 7},
            "test": {"n": 256, "noise": 0.1, "seed": 1234},
            "validation": {"n": 64, "noise": 0.1},
        },
    }


def test_positional_arguments_are_assembled_like_any_list(tmp_path: Path):
    (tmp_path / "step.yaml").write_text("$base: {seconds: 30}\nminutes: 1\n")
    experiment_path = tmp_path / "experiment.yaml"
    experiment_path.write_text(
        "ranges:\n"
        "  $each: {$target: builtins.range, $args: [3]}\n"
        "  short: {}\n"
        "  long: {$base: {$args: [0, 10, 2]}, $args: [7]}\n"
        "  wide: {}\n"
        "steps:\n"
        "  $target: builtins.list\n"
        "  $args:\n"
        "    - [~include step.yaml]\n"
    )
    config = load_config(experiment_path, ["ranges.wide.$args=[1, 5]"])
    assert instantiate(config.ranges.short) == range(3)
    assert instantiate(config.ranges.long) == range(7)
    assert instantiate(config.ranges.wide) == range(1, 5)
    assert instantiate(config.steps) == [{"seconds": 30, "minutes": 1}]


def test_assembled_config_is_instantiated(tmp_path: Path):
    (tmp_path / "limits.yaml").write_text(
        "$each: {$target: datetime.timedelta, seconds: 30}\n"
        "short: {}\n"
        "long: {hours: '${hours}'}\n"
    )
    experiment_path = tmp_path / "experiment.yaml"
    experiment_path.write_text(
        "$target: builtins.dict\n"
        "$meta: {title: Timeouts}\n"
        "hours: 1\n"
        "limits: ~include limits.yaml\n"
        "clock: {$symbol: datetime.datetime}\n"
    )
    config = load_config(experiment_path, ["hours=2"])
    experiment = instantiate(config)
    assert experiment == {
        "hours": 2,
        "limits": {
            "short": datetime.timedelta(seconds=30),
            "long": datetime.timedelta(hours=2, seconds=30),
        },
        "clock": datetime.datetime,
    }
