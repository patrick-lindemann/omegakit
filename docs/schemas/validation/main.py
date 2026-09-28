from pathlib import Path

from project import Experiment

from omegakit import ConfigValidationError, load_config, validate

configs = Path(__file__).parents[2] / "example" / "configs"
experiment = configs / "experiments" / "mlp.yaml"

validate(load_config(experiment), schema=Experiment)

for override in ["model.hidden=wide", "model.activation=gelu"]:
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
