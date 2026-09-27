from pathlib import Path

from curvefit import Experiment

from omegakit import ConfigValidationError, load_config, validate

shared = Path(__file__).parent / "shared-run"

config = load_config(shared / "config.yaml", import_root=shared)
try:
    validate(config, schema=Experiment, allowed_modules=["curvefit"])
except ConfigValidationError as error:
    print(error)
