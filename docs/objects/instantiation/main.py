from collections.abc import Callable
from dataclasses import dataclass

import torch

from omegakit import ConfigValidationError, instantiate, load_config, prepare


@dataclass
class Experiment:
    model: torch.nn.Module
    optimizer: Callable[..., torch.optim.Optimizer]
    loss: Callable[..., torch.Tensor]


config = load_config("experiment.yaml")
experiment = instantiate(config, schema=Experiment)
print("experiment.model:", experiment.model)
print("experiment.loss:", experiment.loss.__name__)

optimizer = experiment.optimizer(experiment.model.parameters())
print("optimizer:", type(optimizer).__name__)
print("lr:", optimizer.param_groups[0]["lr"])
optimizer = experiment.optimizer(experiment.model.parameters(), lr=0.01)
print("lr:", optimizer.param_groups[0]["lr"])

make_model = prepare(config.model)
print("make_model(out_features=3):", make_model(out_features=3))

try:
    instantiate(
        config,
        schema=Experiment,
        overrides=["model.$class=subprocess.Popen"],
        allowed_modules=["torch.nn", "torch.optim"],
    )
except ConfigValidationError as error:
    print("error:", error)
