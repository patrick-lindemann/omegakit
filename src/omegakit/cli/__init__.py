import argparse
import sys
from pathlib import Path

from . import json_schema


def main(arguments: list[str] | None = None) -> None:
    """Run the `omegakit` command line.

    Args:
        arguments: The command-line arguments without the program name. Defaults to
            `None`, which reads them from `sys.argv`.
    """
    parser = argparse.ArgumentParser(prog="omegakit")
    commands = parser.add_subparsers(dest="command", required=True)
    json_schema.register(commands)
    parsed = parser.parse_args(arguments)
    # `python -m` puts the working directory on the path; installed scripts do not.
    if str(Path.cwd()) not in sys.path:
        sys.path.insert(0, str(Path.cwd()))
    parsed.run(parsed)
