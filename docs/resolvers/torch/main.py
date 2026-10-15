import torch

from omegakit import ConfigValidationError, load_config, validate
from omegakit.resolvers.torch import register_torch_resolvers

register_torch_resolvers()
config = load_config("precision.yaml")
print("config.dtype:", config.dtype)
print("config.device:", config.device)
print("config.use_cuda:", config.use_cuda)

model = torch.nn.Linear(1, 1, dtype=config.dtype, device=config.device)
print("model.weight.dtype:", model.weight.dtype)

config = load_config("precision.yaml", overrides=["dtype=${torch.dtype:bfloat}"])
try:
    validate(config)
except ConfigValidationError as error:
    print(f"{type(error).__name__}: {error}")
