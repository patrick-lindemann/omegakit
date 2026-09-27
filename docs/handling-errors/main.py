import sys
from pathlib import Path

from curvefit import Experiment
from omegaconf.errors import OmegaConfBaseException

from omegakit import (
    ConfigValidationError,
    SchemaDefinitionError,
    instantiate,
    load_config,
    validate,
)

configs = "../curvefit/configs"


def run(experiment_file: str, overrides: list[str]) -> None:
    try:
        config = load_config(f"{configs}/{experiment_file}", overrides=overrides)
        validate(config, schema=Experiment)
        experiment = instantiate(config, schema=Experiment)
        print(f"{experiment.name}: {config.run_dir}")
    except FileNotFoundError as error:
        print(f"No such file: {Path(error.filename).name}")
    except OmegaConfBaseException as error:
        print(f"{type(error).__name__}: {error}")


run("experiments/poly3-adam.yaml", ["seed=3"])
run("experiments/poly3-adma.yaml", [])
run("experiments/poly3-adam.yaml", ["trainer.epochs=[50"])
run("experiments/poly3-adam.yaml", ["trainer.epochs=many"])

config = load_config(f"{configs}/base.yaml")
try:
    print(config.name)
except OmegaConfBaseException as error:
    print(type(error).__name__, error, sep=": ")

try:
    run("experiments/poly3-adam.yaml", ["tracker.token=abc"])
except TypeError as error:
    print(error)
    print(error.__notes__)

for degree in ["3", "three", "5"]:
    config = load_config(
        f"{configs}/experiments/poly3-adam.yaml", overrides=[f"model.degree={degree}"]
    )
    try:
        instantiate(config, schema=Experiment)
    except SchemaDefinitionError as error:
        sys.exit(f"Cannot sweep: {error}")
    except ConfigValidationError as error:
        print(f"Skipped degree={degree}: {error}")
        continue
    print(f"Built degree={degree}")
