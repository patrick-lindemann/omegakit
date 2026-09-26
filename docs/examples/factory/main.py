from dataclasses import dataclass
from typing import Any, override

from omegakit import Configurable, instantiate


@dataclass
class AnimalConfig:
    legs: int = 4


class Animal(Configurable[AnimalConfig]):
    def __init__(self, legs: int) -> None:
        self.legs = legs

    @classmethod
    @override
    def from_config(cls, config: AnimalConfig, **kwargs: Any) -> "Animal":
        return Bird(config.legs) if config.legs == 2 else Dog(config.legs)


class Bird(Animal):
    pass


class Dog(Animal):
    pass


assert isinstance(instantiate({"$class": "__main__.Animal", "legs": 2}, Animal), Bird)
assert isinstance(instantiate({"$class": "__main__.Animal"}, Animal), Dog)
