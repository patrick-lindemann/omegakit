import pytest
from project import CONFIGS, Experiment

from omegakit import instantiate, load_config

EXPERIMENTS = sorted((CONFIGS / "experiments").glob("*.yaml"))
ALLOWED = ["project", "torch.nn", "torch.optim"]


@pytest.mark.parametrize("path", EXPERIMENTS, ids=lambda path: path.stem)
def test_experiment_builds(path):
    config = load_config(path, import_root=CONFIGS)
    experiment = instantiate(config, schema=Experiment, allowed_modules=ALLOWED)
    assert experiment.name == path.stem
