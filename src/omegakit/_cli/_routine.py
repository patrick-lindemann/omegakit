import sys
from abc import ABC, abstractmethod
from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import Generic, TypeVar


class Arguments(Namespace, ABC):
    pass


TArgs = TypeVar("TArgs", bound=Arguments)


class Routine(ABC, Generic[TArgs]):
    """A command-line routine."""

    name: str
    help: str
    description: str

    @abstractmethod
    def add_arguments(self, parser: ArgumentParser) -> None: ...

    @abstractmethod
    def run(self, args: TArgs) -> None: ...

    def report_failure(self, path: Path, error: BaseException) -> None:
        message = str(error).splitlines()[0] if str(error) else ""
        print(f"{path}: {type(error).__name__}: {message}", file=sys.stderr)
        for note in getattr(error, "__notes__", []):
            print(note, file=sys.stderr)
