from dataclasses import dataclass
from typing import Literal

from torch import nn

from omegakit import ConfigValidationError, load_config, validate


@dataclass
class Training:
    epochs: int
    schedule: Literal["constant", "cosine"] = "constant"


@dataclass
class Experiment:
    training: Training
    model: nn.Module


validate(load_config("experiment.yaml"), schema=Experiment)

for override in [
    "training.epochs=many",
    "training.schedule=linear",
    "model.$class=torch.optim.SGD",
]:
    try:
        validate(
            load_config("experiment.yaml", overrides=[override]), schema=Experiment
        )
    except ConfigValidationError as error:
        print("error:", error)

validate(load_config("incomplete.yaml"), schema=Experiment, allow_missing=True)
