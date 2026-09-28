import math
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, override

import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset

from omegakit import Configurable


@dataclass
class SineWave(Dataset):
    """Noisy samples of `sin(x)`, at random points between -π and π."""

    n: int
    noise: float
    seed: int
    x: torch.Tensor = field(init=False)
    y: torch.Tensor = field(init=False)

    def __post_init__(self) -> None:
        generator = torch.Generator().manual_seed(self.seed)
        self.x = (torch.rand(self.n, 1, generator=generator) * 2 - 1) * math.pi
        noise = torch.randn(self.n, 1, generator=generator)
        self.y = torch.sin(self.x) + self.noise * noise

    def __len__(self) -> int:
        return self.n

    @override
    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor]:
        return self.x[index], self.y[index]


@dataclass
class MLPConfig:
    hidden: int
    layers: int = 2
    activation: Literal["relu", "tanh"] = "tanh"


class MLP(nn.Module, Configurable[MLPConfig]):
    """A multilayer perceptron from one input to one output."""

    net: nn.Sequential

    def __init__(
        self,
        hidden: int,
        layers: int = 2,
        activation: Literal["relu", "tanh"] = "tanh",
    ) -> None:
        super().__init__()
        activation_class = nn.Tanh if activation == "tanh" else nn.ReLU
        modules: list[nn.Module] = [nn.Linear(1, hidden), activation_class()]
        for _ in range(layers - 1):
            modules += [nn.Linear(hidden, hidden), activation_class()]
        self.net = nn.Sequential(*modules, nn.Linear(hidden, 1))

    @override
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


@dataclass
class Splits:
    """The datasets of an experiment."""

    train: Dataset
    test: Dataset


@dataclass
class Experiment:
    """One training run: what to train, how, and where its results go."""

    name: str
    seed: int
    run_dir: Path
    data: Splits
    model: nn.Module
    optimizer: Callable[..., torch.optim.Optimizer]
    loss: Callable[[torch.Tensor, torch.Tensor], torch.Tensor]
    epochs: int
    batch_size: int = 32


def train(experiment: Experiment) -> float:
    """Train the model on the training split, and return its loss on the test split."""
    model = experiment.model
    optimizer = experiment.optimizer(model.parameters())
    loader = DataLoader(
        experiment.data.train, batch_size=experiment.batch_size, shuffle=True
    )
    for _ in range(experiment.epochs):
        for x, y in loader:
            optimizer.zero_grad()
            experiment.loss(model(x), y).backward()
            optimizer.step()
    x, y = experiment.data.test[:]
    with torch.no_grad():
        return experiment.loss(model(x), y).item()
