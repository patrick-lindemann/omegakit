from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from torch import nn

from omegakit import instantiate, load_config


@dataclass
class Data:
    n: int
    noise: float = 0.1


@dataclass
class Experiment:
    seed: int
    run_dir: Path
    data: Data
    model: nn.Module
    epochs: int = 100


experiment = instantiate(load_config("experiment.yaml"), schema=Experiment)
print("experiment.run_dir:", repr(experiment.run_dir))
print("experiment.data:", experiment.data)
print("experiment.model:", experiment.model)
print("experiment.epochs:", experiment.epochs)


class Loss(Enum):
    MSE = "mean squared error"
    MAE = "mean absolute error"


@dataclass
class Evaluation:
    loss: Loss = Loss.MSE


for value in ["MAE", "mean absolute error"]:
    print(f"loss {value!r}:", instantiate({"loss": value}, schema=Evaluation).loss)
