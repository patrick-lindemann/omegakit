from pathlib import Path
from typing import TypedDict

from omegaconf.errors import OmegaConfBaseException
from torch import nn

from omegakit import (
    ConfigValidationError,
    OmegaKitBaseException,
    instantiate,
    load_config,
    validate,
)


class ExperimentConfig(TypedDict):
    epochs: int
    model: nn.Module


def run(experiment_file: str, overrides: list[str]) -> None:
    try:
        config = load_config(experiment_file, overrides=overrides)
        validate(config, ExperimentConfig)
        model = instantiate(config.model, nn.Module)
        print("epochs:", config.epochs, "model:", model)
    except FileNotFoundError as error:
        print("missing file:", Path(error.filename).name)
    except (OmegaKitBaseException, OmegaConfBaseException) as error:
        print(f"{type(error).__name__}:", error)


run("experiment.yaml", ["epochs=50"])
run("experment.yaml", [])
run("broken.yaml", [])
run("experiment.yaml", ["epochs=many"])

config = load_config("experiment.yaml", overrides=["epochs=many"])
try:
    validate(config, ExperimentConfig)
except ConfigValidationError as error:
    print("error.message:", error.message)
    print("error.full_key:", error.full_key)

config = load_config("untitled.yaml")
try:
    print("config.name:", config.name)
except (OmegaKitBaseException, OmegaConfBaseException) as error:
    print(f"{type(error).__name__}:", error)

try:
    run("experiment.yaml", ["model.hidden=64"])
except TypeError as error:
    print("error:", error)
    print("error.__notes__:", error.__notes__)
