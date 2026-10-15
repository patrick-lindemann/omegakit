from typing import Literal, TypedDict

from torch import nn

from omegakit import ConfigValidationError, is_valid, load_config, validate


class TrainingConfig(TypedDict):
    epochs: int
    schedule: Literal["constant", "cosine"]


class ExperimentConfig(TypedDict):
    training: TrainingConfig
    model: nn.Module


validate(load_config("experiment.yaml"), ExperimentConfig)

for override in [
    "training.epochs=many",
    "training.schedule=linear",
    "model.$target=torch.optim.SGD",
]:
    config = load_config("experiment.yaml", overrides=[override])
    try:
        validate(config, ExperimentConfig)
    except ConfigValidationError as error:
        print(f"{type(error).__name__}:", error)

config = load_config("incomplete.yaml")
print("is_valid:", is_valid(config, ExperimentConfig))
print("allow_missing:", is_valid(config, ExperimentConfig, allow_missing=True))
config = load_config("incomplete.yaml", overrides=["training.schedule=linear"])
try:
    validate(config, ExperimentConfig, allow_missing=True)
except ConfigValidationError as error:
    print(f"{type(error).__name__}:", error)
