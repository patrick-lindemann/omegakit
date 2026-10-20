from pathlib import Path
from typing import TypedDict

from torch import nn
from typing_extensions import NotRequired

from omegakit import ConfigValidationError, load_config, validate


class DataConfig(TypedDict):
    n: int
    noise: NotRequired[float]


class ExperimentConfig(TypedDict):
    seed: int
    run_dir: Path
    data: DataConfig
    model: nn.Module


validate(load_config("experiment.yaml"), ExperimentConfig)
print("experiment.yaml: valid")

for override in ["data.noise=high", "data.size=8", "model=linear"]:
    config = load_config("experiment.yaml", overrides=[override])
    try:
        validate(config, ExperimentConfig)
    except ConfigValidationError as error:
        print(f"{override}: {type(error).__name__}: {error}")
