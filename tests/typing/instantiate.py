import functools
from dataclasses import dataclass

from omegaconf import DictConfig

from omegakit._core.instantiate import instantiate, prepare


@dataclass
class Experiment:
    seed: int = 0


def check_instantiate(config: DictConfig) -> None:
    experiment: Experiment = instantiate(config, Experiment)
    make_experiment: functools.partial[Experiment] = prepare(config, Experiment)
    untyped: int = instantiate(config)
    make_untyped: functools.partial[int] = prepare(config)
    wrong: str = instantiate(config, Experiment)  # ty: ignore[invalid-assignment]
    make_wrong: functools.partial[str] = prepare(config, Experiment)  # ty: ignore[invalid-assignment]
    print(experiment, make_experiment, untyped, make_untyped, wrong, make_wrong)
