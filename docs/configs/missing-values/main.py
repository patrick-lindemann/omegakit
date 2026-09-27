from pathlib import Path

from curvefit import Experiment

from omegakit import ConfigValidationError, load_config, validate

configs = Path(__file__).parents[2] / "curvefit" / "configs"

base = load_config(configs / "base.yaml")
try:
    validate(base, schema=Experiment)
except ConfigValidationError as error:
    print(error)
validate(base, schema=Experiment, allow_missing=True)
