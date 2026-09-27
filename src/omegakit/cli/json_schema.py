import argparse
import json
from pathlib import Path

from omegakit.schema import generate_json_schema
from omegakit.utils import import_object


def register(commands: argparse._SubParsersAction) -> None:
    """Add the `json-schema` command.

    Args:
        commands: The subcommands of the `omegakit` parser.
    """
    parser = commands.add_parser(
        "json-schema", help="generate a JSON Schema for YAML config files"
    )
    parser.add_argument(
        "schema", help="import path of a root schema dataclass or a Configurable class"
    )
    parser.add_argument(
        "-o", "--output", type=Path, help="output file (default: standard output)"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="do not write; exit with 1 if the output file is not up to date",
    )
    parser.set_defaults(run=run, parser=parser)


def run(arguments: argparse.Namespace) -> None:
    """Write the JSON Schema of the class named in `arguments`.

    Args:
        arguments: The parsed `json-schema` arguments.

    Raises:
        SystemExit: With status 1 if `--check` finds the output file out of date.
    """
    parser: argparse.ArgumentParser = arguments.parser
    output: Path | None = arguments.output
    try:
        schema = generate_json_schema(import_object(arguments.schema))
    except ImportError as error:
        parser.error(f"cannot import {arguments.schema}: {error}")
    if arguments.check:
        if output is None:
            parser.error("--check needs -o/--output")
        if not output.exists() or json.loads(output.read_text()) != schema:
            print(f"{output} is out of date; run without --check to update it.")
            raise SystemExit(1)
        return
    text = json.dumps(schema, indent=2) + "\n"
    if output is None:
        print(text, end="")
    else:
        output.write_text(text)
