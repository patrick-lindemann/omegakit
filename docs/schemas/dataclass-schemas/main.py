from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from curvefit import Experiment

from omegakit import instantiate, load_config

experiments = Path(__file__).parents[2] / "curvefit" / "configs" / "experiments"

config = load_config(experiments / "poly3-adam.yaml")
experiment = instantiate(config, schema=Experiment)
print(type(experiment.data).__name__, type(experiment.data.test).__name__)
print(type(experiment.model).__name__, experiment.run_dir.parts)

model = instantiate({"$class": "curvefit.models.Polynomial", "degree": "4"})
print(model.degree + 1)


class Loss(Enum):
    MSE = "mean squared error"
    MAE = "mean absolute error"


@dataclass
class Evaluation:
    loss: Loss = Loss.MSE


for value in ["MAE", "mean absolute error"]:
    print(instantiate({"loss": value}, schema=Evaluation).loss)
