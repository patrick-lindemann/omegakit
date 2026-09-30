import json
from argparse import ArgumentError, ArgumentParser
from pathlib import Path
from typing import override

from omegakit.core.errors import SchemaDefinitionError
from omegakit.core.json_schema import generate_json_schema
from omegakit.core.utils import import_object

from ._arg import Arguments
from ._routine import Routine


class ExportSchemaArguments(Arguments):
    """The parsed arguments of the `export-schema` command."""

    schema: str
    output: Path | None
    check: bool


class ExportSchemaRoutine(Routine[ExportSchemaArguments]):
    """The `export-schema` command, which writes the JSON Schema of a class."""

    name = "export-schema"
    help = "generate a JSON Schema for YAML config files"
    description = "Generate a JSON Schema for YAML config files."

    @override
    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "schema",
            help="import path of a dataclass or a Configurable class",
        )
        parser.add_argument(
            "-o",
            "--output",
            type=Path,
            help="output file (default: standard output)",
        )
        parser.add_argument(
            "--check",
            action="store_true",
            help="do not write; exit with 1 if the output file is not up to date",
        )

    @override
    def run(self, args: ExportSchemaArguments) -> None:
        """Write the JSON Schema of the class named in `args`.

        Args:
            args: The parsed `export-schema` arguments.

        Raises:
            ArgumentError: If the class cannot be imported or exported, or `--check`
                is given without `--output`.
            SystemExit: With status 1 if `--check` finds the output file out of date.
        """
        try:
            target = import_object(args.schema)
        except ImportError as error:
            raise ArgumentError(
                None, f"cannot import {args.schema}: {error}"
            ) from error
        try:
            schema = generate_json_schema(target)
        except (TypeError, SchemaDefinitionError) as error:
            raise ArgumentError(
                None, f"cannot export {args.schema}: {error}"
            ) from error
        output = args.output
        if args.check:
            if output is None:
                raise ArgumentError(None, "--check needs -o/--output")
            if not output.exists() or json.loads(output.read_text()) != schema:
                print(f"{output} is out of date; run without --check to update it.")
                raise SystemExit(1)
            return
        text = json.dumps(schema, indent=2) + "\n"
        if output is None:
            print(text, end="")
        else:
            output.write_text(text)
