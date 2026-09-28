import torch

from omegakit import load_config
from omegakit.resolvers.torch import register_torch_resolvers

register_torch_resolvers()
config = load_config("precision.yaml")
print("config.dtype:", config.dtype)
print("config.use_cuda:", config.use_cuda)

model = torch.nn.Linear(1, 1, dtype=config.dtype)
print("model.weight.dtype:", model.weight.dtype)
