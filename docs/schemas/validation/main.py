from pathlib import Path

from curvefit import Experiment

from omegakit import ConfigValidationError, load_config, validate

configs = Path(__file__).parents[2] / "curvefit" / "configs"
experiment = configs / "experiments" / "poly3-adam.yaml"

validate(load_config(experiment), schema=Experiment)

for override in ["model.degree=three", "trainer.schedule=linear"]:
    config = load_config(experiment, overrides=[override])
    try:
        validate(config, schema=Experiment)
    except ConfigValidationError as error:
        print(error)

config = load_config(experiment)
config.model = config.data.train
try:
    validate(config, schema=Experiment)
except ConfigValidationError as error:
    print(error)

base = load_config(configs / "base.yaml")
validate(base, schema=Experiment, allow_missing=True)
