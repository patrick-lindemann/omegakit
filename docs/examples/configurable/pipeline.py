from collections.abc import Mapping
from typing import Any, Self, override

from omegakit import Configurable


class Step:
    def __init__(self, name: str) -> None:
        self.name = name


class Pipeline(Configurable):
    def __init__(self, steps: list[Step], retries: int = 0) -> None:
        self.steps = steps
        self.retries = retries


class NamedPipeline(Configurable):
    def __init__(self, steps: list[Step]) -> None:
        self.steps = steps

    @classmethod
    @override
    def from_config(cls, config: Mapping[str, Any], **kwargs: Any) -> Self:
        return cls([Step(name) for name in config["step_names"]], **kwargs)


class Registry:
    """Not a `Configurable`: any class with a `from_config` is called the same way."""

    def __init__(self, names: list[str]) -> None:
        self.names = names

    @classmethod
    def from_config(cls, config: Mapping[str, Any], **kwargs: Any) -> "Registry":
        return cls(sorted(config["names"]))
