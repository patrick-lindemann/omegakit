from pathlib import Path

import pytest
from project import CONFIGS, Experiment

from omegakit import instantiate, load_config

EXPERIMENTS = sorted((CONFIGS / "experiments").glob("*.yaml"))


@pytest.mark.parametrize("file_path", EXPERIMENTS, ids=lambda file_path: file_path.stem)
def test_experiment_builds(file_path: Path) -> None:
    config = load_config(file_path, include_root=CONFIGS)
    experiment = instantiate(config, Experiment)
    assert experiment.name == file_path.stem
