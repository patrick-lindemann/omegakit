import torch
from project import CONFIGS, MLP, Experiment

from omegakit import (
    PARTIAL_KEY,
    ConfigValidationError,
    instantiate,
    load_config,
    make_node,
)

config = load_config(CONFIGS / "experiments/linear.yaml")
config.model = make_node(MLP, hidden=16)
config.optimizer = {**make_node(torch.optim.Adam, lr=0.01), PARTIAL_KEY: True}
experiment = instantiate(config, schema=Experiment)
optimizer = experiment.optimizer(experiment.model.parameters())
print("model:", type(experiment.model).__name__)
print("optimizer:", type(optimizer).__name__)

config.data.test = make_node(MLP, hidden=8)
try:
    instantiate(config, schema=Experiment)
except ConfigValidationError as error:
    print("error:", error)

config = load_config(
    CONFIGS / "experiments/linear.yaml", overrides=["optimizer.$class=torch.optim.Adam"]
)
experiment = instantiate(config, schema=Experiment)
try:
    experiment.optimizer(experiment.model.parameters())
except TypeError as error:
    print("error:", error)
