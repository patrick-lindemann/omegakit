import math
from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Any, override

from curvefit.models import Parameter


class Optimizer(ABC):
    """Updates parameters from their gradients, as `torch.optim` optimizers do."""

    param_groups: list[dict[str, Any]]
    state: dict[Parameter, dict[str, float]]

    def __init__(self, params: Iterable[Parameter], defaults: dict[str, Any]) -> None:
        self.param_groups = [{"params": list(params), **defaults}]
        self.state = {}

    @abstractmethod
    def step(self) -> None:
        """Update every parameter once."""

    def zero_grad(self) -> None:
        for group in self.param_groups:
            for parameter in group["params"]:
                parameter.grad = 0.0


class SGD(Optimizer):
    """Stochastic gradient descent with momentum, as `torch.optim.SGD`."""

    def __init__(
        self, params: Iterable[Parameter], lr: float, momentum: float = 0.0
    ) -> None:
        super().__init__(params, {"lr": lr, "momentum": momentum})

    @override
    def step(self) -> None:
        for group in self.param_groups:
            for parameter in group["params"]:
                state = self.state.setdefault(parameter, {"buffer": 0.0})
                state["buffer"] = group["momentum"] * state["buffer"] + parameter.grad
                parameter.value -= group["lr"] * state["buffer"]


class Adam(Optimizer):
    """Adam, as `torch.optim.Adam`."""

    def __init__(
        self,
        params: Iterable[Parameter],
        lr: float = 1e-3,
        betas: tuple[float, float] = (0.9, 0.999),
        eps: float = 1e-8,
    ) -> None:
        super().__init__(params, {"lr": lr, "betas": betas, "eps": eps})

    @override
    def step(self) -> None:
        for group in self.param_groups:
            beta1, beta2 = group["betas"]
            for parameter in group["params"]:
                state = self.state.setdefault(
                    parameter, {"step": 0, "mean": 0.0, "variance": 0.0}
                )
                state["step"] += 1
                state["mean"] = beta1 * state["mean"] + (1 - beta1) * parameter.grad
                state["variance"] = (
                    beta2 * state["variance"] + (1 - beta2) * parameter.grad**2
                )
                mean = state["mean"] / (1 - beta1 ** state["step"])
                variance = state["variance"] / (1 - beta2 ** state["step"])
                parameter.value -= (
                    group["lr"] * mean / (math.sqrt(variance) + group["eps"])
                )
