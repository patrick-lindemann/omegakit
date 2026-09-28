from pathlib import Path

from project import Experiment

from omegakit import ConfigValidationError, load_config, validate

shared = Path(__file__).parent / "shared-run"
allowed = ["project", "torch.nn", "torch.optim"]

config = load_config(shared / "config.yaml", import_root=shared)
try:
    validate(config, schema=Experiment, allowed_modules=allowed)
except ConfigValidationError as error:
    print(error)
