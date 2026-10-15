from collections.abc import Callable
from dataclasses import dataclass

import torch
from torch import nn


@dataclass
class Experiment:
    """One training run: what to train and how."""

    model: nn.Module
    optimizer: Callable[..., torch.optim.Optimizer]
    loss: Callable[[torch.Tensor, torch.Tensor], torch.Tensor]
    epochs: int
    batch_size: int = 32
