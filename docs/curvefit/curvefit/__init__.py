from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from curvefit.data import Dataset
from curvefit.models import Model
from curvefit.optim import Optimizer
from curvefit.tracking import Tracker
from curvefit.trainer import Trainer


@dataclass
class Splits:
    """The datasets of an experiment."""

    train: Dataset
    validation: Dataset
    test: Dataset


@dataclass
class Experiment:
    """One run: what to fit, how, and where its results go."""

    name: str
    seed: int
    run_dir: Path
    data: Splits
    model: Model
    optimizer: Callable[..., Optimizer]
    trainer: Trainer
    metrics: dict[str, Callable[[list[float], list[float]], float]]
    tracker: Tracker | None = None
