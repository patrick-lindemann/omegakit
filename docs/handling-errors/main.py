from dataclasses import dataclass
from pathlib import Path

from omegaconf.errors import OmegaConfBaseException
from torch import nn

from omegakit import instantiate, load_config


@dataclass
class Experiment:
    epochs: int
    model: nn.Module


def run(experiment_file: str, overrides: list[str]) -> None:
    try:
        config = load_config(experiment_file, overrides=overrides)
        experiment = instantiate(config, schema=Experiment)
        print("experiment.epochs:", experiment.epochs)
    except FileNotFoundError as error:
        print("missing file:", Path(error.filename).name)
    except OmegaConfBaseException as error:
        print(f"{type(error).__name__}:", error)


run("experiment.yaml", ["epochs=50"])
run("experment.yaml", [])
run("experiment.yaml", ["epochs=[50"])
run("experiment.yaml", ["epochs=many"])

import sys

from omegakit import ConfigValidationError, SchemaDefinitionError

for epochs in ["10", "many", "20"]:
    config = load_config("experiment.yaml", overrides=[f"epochs={epochs}"])
    try:
        instantiate(config, schema=Experiment)
    except SchemaDefinitionError as error:
        sys.exit(f"Cannot sweep: {error}")
    except ConfigValidationError as error:
        print(f"skipped epochs={epochs}:", error)
        continue
    print(f"built epochs={epochs}")

config = load_config("untitled.yaml")
try:
    print("config.name:", config.name)
except OmegaConfBaseException as error:
    print(f"{type(error).__name__}:", error)

try:
    run("experiment.yaml", ["model.hidden=64"])
except TypeError as error:
    print("error:", error)
    print("error.__notes__:", error.__notes__)
