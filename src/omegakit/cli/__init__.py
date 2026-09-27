import argparse
import sys
from pathlib import Path

from omegaconf import OmegaConf

from omegakit.resolvers.secrets import register_secret_resolver

from . import check, json_schema, show


def main(arguments: list[str] | None = None) -> None:
    """Run the `omegakit` command line.

    Args:
        arguments: The command-line arguments without the program name. Defaults to
            `None`, which reads them from `sys.argv`.
    """
    parser = argparse.ArgumentParser(prog="omegakit")
    commands = parser.add_subparsers(dest="command", required=True)
    check.register(commands)
    show.register(commands)
    json_schema.register(commands)
    parsed = parser.parse_args(arguments)
    if not OmegaConf.has_resolver("secret"):
        register_secret_resolver()
    # `python -m` puts the working directory on the path; installed scripts do not.
    if str(Path.cwd()) not in sys.path:
        sys.path.insert(0, str(Path.cwd()))
    parsed.run(parsed)
