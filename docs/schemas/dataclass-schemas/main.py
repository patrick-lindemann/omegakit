from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from project import Experiment

from omegakit import instantiate, load_config

experiments = Path(__file__).parents[2] / "example" / "configs" / "experiments"

config = load_config(experiments / "mlp.yaml")
experiment = instantiate(config, schema=Experiment)
print(type(experiment.data).__name__, type(experiment.data.test).__name__)
print(type(experiment.model).__name__, experiment.run_dir.parts)

data = instantiate({"$class": "project.SineWave", "n": "64", "noise": 0.1, "seed": 0})
print(len(data))


class Loss(Enum):
    MSE = "mean squared error"
    MAE = "mean absolute error"


@dataclass
class Evaluation:
    loss: Loss = Loss.MSE


for value in ["MAE", "mean absolute error"]:
    print(instantiate({"loss": value}, schema=Evaluation).loss)
