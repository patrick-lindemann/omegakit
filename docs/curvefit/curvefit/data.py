import csv
import math
import random
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import override


def sine(x: float) -> float:
    return math.sin(math.pi * x)


def cubic(x: float) -> float:
    return x**3 - 0.5 * x


class Dataset(ABC):
    """Samples of a curve."""

    @abstractmethod
    def samples(self) -> tuple[list[float], list[float]]:
        """The x values and the y values."""


@dataclass
class Synthetic(Dataset):
    """Noisy samples of a function at random points between -1 and 1."""

    function: Callable[[float], float]
    noise: float
    n: int
    seed: int

    @override
    def samples(self) -> tuple[list[float], list[float]]:
        # Its own generator, so the samples depend only on `seed`.
        generator = random.Random(self.seed)
        xs = [generator.uniform(-1.0, 1.0) for _ in range(self.n)]
        ys = [self.function(x) + generator.gauss(0.0, self.noise) for x in xs]
        return xs, ys


@dataclass
class CsvData(Dataset):
    """Measurements from a CSV file with the columns `x` and `y`."""

    path: Path

    @override
    def samples(self) -> tuple[list[float], list[float]]:
        with self.path.open(newline="") as file:
            rows = list(csv.DictReader(file))
        return [float(row["x"]) for row in rows], [float(row["y"]) for row in rows]
