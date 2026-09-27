from typing import override

import torch
from curvefit.models import Model


class Polynomial(torch.nn.Module, Model):
    """A polynomial of a given degree, as a PyTorch module."""

    degree: int
    dtype: torch.dtype
    coefficients: torch.nn.Parameter

    def __init__(
        self, degree: int, init_scale: float = 0.1, dtype: torch.dtype = torch.float32
    ) -> None:
        super().__init__()
        self.degree = degree
        self.dtype = dtype
        self.coefficients = torch.nn.Parameter(
            torch.randn(degree + 1, dtype=dtype) * init_scale
        )

    @override
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        powers = x.unsqueeze(-1) ** torch.arange(self.degree + 1)
        return powers @ self.coefficients

    @override
    def predict(self, xs: list[float]) -> list[float]:
        with torch.no_grad():
            return self(torch.tensor(xs, dtype=self.dtype)).tolist()

    @override
    def backward(self, xs: list[float], ys: list[float]) -> float:
        predictions = self(torch.tensor(xs, dtype=self.dtype))
        loss = torch.nn.functional.mse_loss(
            predictions, torch.tensor(ys, dtype=self.dtype)
        )
        loss.backward()
        return loss.item()
