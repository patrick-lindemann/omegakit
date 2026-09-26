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
    parser.set_defaults(run=run)


def run(arguments: argparse.Namespace) -> None:
    """Write the JSON Schema of the class named in `arguments`.

    Args:
        arguments: The parsed `json-schema` arguments.
    """
    schema = generate_json_schema(import_object(arguments.schema))
    text = json.dumps(schema, indent=2) + "\n"
    if arguments.output is None:
        print(text, end="")
    else:
        arguments.output.write_text(text)
