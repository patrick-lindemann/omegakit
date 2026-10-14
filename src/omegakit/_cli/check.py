from argparse import ArgumentError, ArgumentParser
from pathlib import Path
from typing import override

from omegakit._core.errors import QualifiedNameSyntaxError
from omegakit._core.load import load_config
from omegakit._core.schema import validate
from omegakit._core.utils.locate import locate

from ._args import Arguments
from ._routine import Routine


class CheckArguments(Arguments):
    """The parsed arguments of the `check` command."""

    configs: list[Path]
    overrides: list[str] | None
    schema: str | None
    include_root: Path | None


class CheckRoutine(Routine[CheckArguments]):
    """The `check` command, which loads and validates config files."""

    name = "check"
    help = "load and validate config files"
    description = "Load and validate config files."

    @override
    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "configs",
            nargs="+",
            type=Path,
            metavar="CONFIG",
            help="config files",
        )
        parser.add_argument(
            "--overrides",
            action="extend",
            nargs="+",
            metavar="KEY=VALUE",
            help="set values in every file, such as model.depth=3",
        )
        parser.add_argument(
            "--schema",
            metavar="QUALIFIED_NAME",
            help="class the root of every file must match, such as myapp.AppConfig",
        )
        parser.add_argument(
            "--include-root",
            type=Path,
            metavar="DIR",
            help="reject any ~include of a file outside DIR",
        )

    @override
    def run(self, args: CheckArguments) -> None:
        if args.include_root is not None and not args.include_root.is_dir():
            raise ArgumentError(
                None, f"--include-root {args.include_root} is not a directory"
            )
        schema = None
        if args.schema is not None:
            try:
                schema = locate(args.schema)
            except (QualifiedNameSyntaxError, ImportError) as error:
                raise ArgumentError(None, f"cannot import --schema: {error}") from error
            if not isinstance(schema, type):
                raise ArgumentError(None, f"--schema {args.schema} is not a class")
        invalid = 0
        for path in args.configs:
            try:
                config = load_config(
                    path, overrides=args.overrides, include_root=args.include_root
                )
                validate(config, schema)
            # A module that exits while it is imported must not pass the check.
            except (Exception, SystemExit) as error:
                invalid += 1
                self.report_failure(path, error)
        if invalid:
            raise SystemExit(1)
