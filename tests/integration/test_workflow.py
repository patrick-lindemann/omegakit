from pathlib import Path
from types import ModuleType

import pytest

from omegakit._core.errors import ConfigSchemaError, ConfigValidationError
from omegakit._core.instantiate import instantiate, prepare
from omegakit._core.load import load_config
from omegakit._core.validate import validate


def test_files_are_loaded_checked_and_built(tmp_path: Path, targets: ModuleType):
    (tmp_path / "model.yaml").write_text(
        "$target: config_targets.Model\ndepth: '3'\nactivation: relu\n"
    )
    path = tmp_path / "experiment.yaml"
    path.write_text(
        "$target: config_targets.Experiment\n"
        "model: ~include model.yaml\n"
        "optimizer: {$target: config_targets.Optimizer, lr: 0.5}\n"
    )
    config = load_config(path, ["seed=3"])
    validate(config, targets.Experiment)
    assert targets.CALLS == []
    experiment = instantiate(config, targets.Experiment)
    assert experiment.model.config == {"depth": 3, "activation": "relu"}
    assert experiment.optimizer.lr == 0.5
    assert experiment.seed == 3


def test_base_that_an_override_gives_is_rejected(tmp_path: Path, targets: ModuleType):
    path = tmp_path / "experiment.yaml"
    path.write_text("model: {$target: config_targets.Model, depth: 2}\n")
    config = load_config(path, ["model.$base={activation: tanh}"])
    with pytest.raises(ConfigValidationError, match=r"\$base") as error_info:
        validate(config)
    assert error_info.value.full_key == "model"


def test_target_of_each_is_checked_in_every_child(tmp_path: Path, targets: ModuleType):
    path = tmp_path / "experiment.yaml"
    path.write_text(
        "models:\n"
        "  $each: {$target: config_targets.Model, depth: 2}\n"
        "  small: {}\n"
        "  wide: {dpeth: 4}\n"
    )
    config = load_config(path)
    with pytest.raises(ConfigSchemaError, match="dpeth") as error_info:
        validate(config)
    assert error_info.value.full_key == "models.wide"
    del config.models.wide.dpeth
    models = instantiate({"$target": "builtins.dict", **config.models})
    assert models["small"].config == {"depth": 2}


def test_kept_meta_is_no_argument(tmp_path: Path, targets: ModuleType):
    path = tmp_path / "experiment.yaml"
    path.write_text(
        "$meta: {title: Baseline}\n"
        "model: {$target: config_targets.Model, $meta: {note: small}, depth: 2}\n"
    )
    config = load_config(path, keep_meta=True)
    validate(config)
    model = instantiate(config.model)
    assert model.config == {"depth": 2}
    assert model.kwargs == {}


def test_prepared_target_takes_its_positions_from_the_file(tmp_path: Path):
    path = tmp_path / "number.yaml"
    path.write_text("$target: builtins.int\n$args: [ff]\n")
    make_number = prepare(load_config(path))
    assert make_number(base=16) == 255
