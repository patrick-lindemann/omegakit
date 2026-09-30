from abc import ABC
from argparse import Namespace


class Arguments(Namespace, ABC):
    """The base of the parsed arguments of a command."""

    pass
