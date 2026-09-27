from pathlib import Path

import pytest
from curvefit import Experiment

from omegakit import instantiate, load_config

CONFIGS = Path(__file__).parents[2] / "curvefit" / "configs"
EXPERIMENTS = sorted((CONFIGS / "experiments").glob("*.yaml"))


@pytest.mark.parametrize("path", EXPERIMENTS, ids=lambda path: path.stem)
def test_experiment_builds(path):
    config = load_config(path, import_root=CONFIGS)
    experiment = instantiate(config, schema=Experiment, allowed_modules=["curvefit"])
    assert experiment.name == path.stem
