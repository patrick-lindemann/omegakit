from abc import ABC, abstractmethod
from argparse import ArgumentParser

from ._args import Arguments


class Routine[TArgs: Arguments](ABC):
    """A command of the `omegakit` command line."""

    name: str
    help: str
    description: str

    @abstractmethod
    def add_arguments(self, parser: ArgumentParser) -> None: ...

    @abstractmethod
    def run(self, args: TArgs) -> None: ...
