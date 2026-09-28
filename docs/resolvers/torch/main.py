from pathlib import Path

import torch

from omegakit import load_config
from omegakit.resolvers.torch import register_torch_resolvers

register_torch_resolvers()
config = load_config(Path(__file__).parent / "precision.yaml")

model = torch.nn.Linear(1, 1, dtype=config.dtype)
print(config.dtype, model.weight.dtype, config.use_cuda)
