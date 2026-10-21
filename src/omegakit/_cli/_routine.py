import sys
from abc import ABC, abstractmethod
from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import Generic, TypeVar


class Arguments(Namespace, ABC):
    """The parsed command-line arguments of a routine."""


TArgs = TypeVar("TArgs", bound=Arguments)


class Routine(ABC, Generic[TArgs]):
    """A command-line routine."""

    name: str
    help: str
    description: str

    @abstractmethod
    def add_arguments(self, parser: ArgumentParser) -> None:
        """Add the arguments of the routine to its parser.

        Args:
            parser: The parser of the routine's subcommand.
        """

    @abstractmethod
    def run(self, args: TArgs) -> None:
        """Run the routine.

        Args:
            args: The parsed arguments.
        """

    def report_failure(self, path: Path, error: BaseException) -> None:
        """Print the error of a config file, and its notes, to stderr.

        Args:
            path: The config file.
            error: The error.
        """
        message = str(error).splitlines()[0] if str(error) else ""
        print(f"{path}: {type(error).__name__}: {message}", file=sys.stderr)
        for note in getattr(error, "__notes__", []):
            print(note, file=sys.stderr)
