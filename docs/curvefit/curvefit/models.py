import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, override


class Parameter:
    """A trainable number and its gradient."""

    value: float
    grad: float

    def __init__(self, value: float) -> None:
        self.value = value
        self.grad = 0.0


class Model(ABC):
    """A curve with trainable parameters."""

    @abstractmethod
    def parameters(self) -> list[Any]:
        """The parameters that the optimizer updates."""

    @abstractmethod
    def predict(self, xs: list[float]) -> list[float]:
        """The model's y value at each x."""

    @abstractmethod
    def backward(self, xs: list[float], ys: list[float]) -> float:
        """Set each parameter's gradient of the mean squared error, and return it."""


@dataclass
class Polynomial(Model):
    """A polynomial of a given degree, fitted by its coefficients."""

    degree: int
    init_scale: float = 0.1
    coefficients: list[Parameter] = field(init=False)

    def __post_init__(self) -> None:
        # Random initial coefficients, so a run depends on the seed.
        self.coefficients = [
            Parameter(random.gauss(0.0, self.init_scale))
            for _ in range(self.degree + 1)
        ]

    @override
    def parameters(self) -> list[Parameter]:
        return self.coefficients

    @override
    def predict(self, xs: list[float]) -> list[float]:
        return [
            sum(c.value * x**power for power, c in enumerate(self.coefficients))
            for x in xs
        ]

    @override
    def backward(self, xs: list[float], ys: list[float]) -> float:
        errors = [
            prediction - y for prediction, y in zip(self.predict(xs), ys, strict=True)
        ]
        for power, coefficient in enumerate(self.coefficients):
            coefficient.grad = (
                2 * sum(e * x**power for e, x in zip(errors, xs, strict=True)) / len(xs)
            )
        return sum(e * e for e in errors) / len(xs)


@dataclass
class Linear(Polynomial):
    """A straight line: a polynomial of degree 1."""

    degree: int = field(default=1, init=False)
