import math
from abc import abstractmethod
from dataclasses import dataclass
from typing import Any, Literal, override

from curvefit.data import Dataset
from curvefit.metrics import mse
from curvefit.models import Model
from curvefit.tracking import Tracker
from omegakit import Configurable


@dataclass
class TrainerConfig:
    epochs: int
    schedule: Literal["constant", "cosine"] = "constant"


class Trainer(Configurable[TrainerConfig]):
    """Fits a model with an optimizer, one full pass over the data per epoch."""

    epochs: int

    def __init__(self, epochs: int) -> None:
        self.epochs = epochs

    @classmethod
    @override
    def from_config(cls, config: TrainerConfig, **kwargs: Any) -> "Trainer":
        if config.schedule == "cosine":
            return CosineTrainer(config.epochs, **kwargs)
        return ConstantTrainer(config.epochs, **kwargs)

    @abstractmethod
    def learning_rate(self, initial: float, epoch: int) -> float:
        """The learning rate for an epoch."""

    def fit(
        self,
        model: Model,
        optimizer: Any,
        train: Dataset,
        validation: Dataset,
        tracker: Tracker | None = None,
    ) -> float:
        xs, ys = train.samples()
        validation_xs, validation_ys = validation.samples()
        loss = math.nan
        for epoch in range(self.epochs):
            for group in optimizer.param_groups:
                group.setdefault("initial_lr", group["lr"])
                group["lr"] = self.learning_rate(group["initial_lr"], epoch)
            optimizer.zero_grad()
            loss = model.backward(xs, ys)
            optimizer.step()
            if tracker is not None:
                validation_loss = mse(model.predict(validation_xs), validation_ys)
                tracker.log(epoch, loss=loss, validation_loss=validation_loss)
        return loss


class ConstantTrainer(Trainer):
    """Keeps the optimizer's learning rate."""

    @override
    def learning_rate(self, initial: float, epoch: int) -> float:
        return initial


class CosineTrainer(Trainer):
    """Lowers the learning rate along a cosine, to zero after the last epoch."""

    @override
    def learning_rate(self, initial: float, epoch: int) -> float:
        return initial * (1 + math.cos(math.pi * epoch / self.epochs)) / 2
