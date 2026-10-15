import sys
from argparse import ArgumentError, ArgumentParser
from pathlib import Path
from typing import Any

from . import __version__
from ._cli import ROUTINES, Arguments, Routine
from .resolvers.secrets import register_secret_resolver


class _MainArguments(Arguments):
    """The parsed arguments of the `omegakit` command line."""

    command: str
    routine: Routine[Any]
    parser: ArgumentParser


def main(argv: list[str] | None = None) -> None:
    """Run the `omegakit` command line.

    Args:
        argv: The command-line arguments without the program name. Defaults to
            `None`, which reads them from `sys.argv`.
    """
    parser = ArgumentParser(prog="omegakit")
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for routine in ROUTINES:
        subparser = subparsers.add_parser(
            routine.name, help=routine.help, description=routine.description
        )
        routine.add_arguments(subparser)
        subparser.set_defaults(routine=routine, parser=subparser)
    args = parser.parse_args(argv, namespace=_MainArguments())
    register_secret_resolver(replace=True)
    # `python -m` puts the working directory on the path; installed scripts do not.
    if str(Path.cwd()) not in sys.path:
        sys.path.insert(0, str(Path.cwd()))
    try:
        args.routine.run(args)
    except ArgumentError as error:
        args.parser.error(str(error))


if __name__ == "__main__":
    main()
