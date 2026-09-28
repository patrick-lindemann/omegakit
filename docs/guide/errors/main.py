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
