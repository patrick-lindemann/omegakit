import torch
import torch.nn.functional as F
from project import CONFIGS, Experiment
from torch.utils.data import DataLoader

from omegakit import ConfigValidationError, instantiate, load_config

config = load_config("experiment.yaml")
model = instantiate(config.model)
print("model:", model)

torch.manual_seed(0)
model = instantiate(config.model)
data = instantiate(config.data)
optimizer = instantiate(config.optimizer)(model.parameters())

for _ in range(100):
    for x, y in DataLoader(data, batch_size=32, shuffle=True):
        optimizer.zero_grad()
        F.mse_loss(model(x), y).backward()
        optimizer.step()
x, y = data[:]
print("loss:", round(F.mse_loss(model(x), y).item(), 3))

config = load_config(CONFIGS / "experiments/mlp.yaml", overrides=["model.hiden=64"])
try:
    instantiate(config, schema=Experiment)
except ConfigValidationError as error:
    print("error:", error)
