import sys
from pathlib import Path

from omegaconf.errors import OmegaConfBaseException
from project import Experiment

from omegakit import (
    ConfigValidationError,
    SchemaDefinitionError,
    instantiate,
    load_config,
    validate,
)

configs = "../example/configs"


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


run("experiments/mlp.yaml", ["seed=3"])
run("experiments/mpl.yaml", [])
run("experiments/mlp.yaml", ["epochs=[50"])
run("experiments/mlp.yaml", ["epochs=many"])

config = load_config(f"{configs}/base.yaml")
try:
    print(config.name)
except OmegaConfBaseException as error:
    print(type(error).__name__, error, sep=": ")

try:
    run("experiments/linear.yaml", ["model.hidden=64"])
except TypeError as error:
    print(error)
    print(error.__notes__)

for hidden in ["8", "wide", "32"]:
    config = load_config(
        f"{configs}/experiments/mlp.yaml", overrides=[f"model.hidden={hidden}"]
    )
    try:
        instantiate(config, schema=Experiment)
    except SchemaDefinitionError as error:
        sys.exit(f"Cannot sweep: {error}")
    except ConfigValidationError as error:
        print(f"Skipped hidden={hidden}: {error}")
        continue
    print(f"Built hidden={hidden}")
