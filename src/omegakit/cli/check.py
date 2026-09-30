from argparse import ArgumentError, ArgumentParser
from pathlib import Path
from typing import override

from omegakit.core.load import load_config
from omegakit.core.utils import import_object
from omegakit.core.validate import validate

from ._arg import Arguments
from ._routine import Routine


class CheckArguments(Arguments):
    """The parsed arguments of the `check` command."""

    configs: list[Path]
    overrides: list[str] | None
    schema: str | None
    allow_missing: bool
    allowed_modules: list[str] | None
    import_root: Path | None


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
            metavar="IMPORT_PATH",
            help="class the root of every file must match, such as myapp.AppConfig",
        )
        parser.add_argument(
            "--allow-missing",
            action="store_true",
            help="accept ??? and other missing values, as in library files",
        )
        parser.add_argument(
            "--allow-module",
            action="append",
            dest="allowed_modules",
            metavar="NAME",
            help="allow $class and $ref only from this module and its submodules; "
            "repeatable (default: any module)",
        )
        parser.add_argument(
            "--import-root",
            type=Path,
            metavar="DIR",
            help="reject any ~import of a file outside DIR",
        )

    @override
    def run(self, args: CheckArguments) -> None:
        if args.import_root is not None and not args.import_root.is_dir():
            raise ArgumentError(
                None, f"--import-root {args.import_root} is not a directory"
            )
        schema = None
        if args.schema is not None:
            try:
                schema = import_object(args.schema)
            except ImportError as error:
                raise ArgumentError(None, f"cannot import --schema: {error}") from error
            if not isinstance(schema, type):
                raise ArgumentError(None, f"--schema {args.schema} is not a class")
        invalid = 0
        for path in args.configs:
            try:
                config = load_config(
                    path, overrides=args.overrides, import_root=args.import_root
                )
                validate(
                    config,
                    schema=schema,
                    allow_missing=args.allow_missing,
                    allowed_modules=args.allowed_modules,
                )
            # A module that exits while it is imported must not pass the check.
            except (Exception, SystemExit) as error:
                invalid += 1
                message = str(error).splitlines()[0] if str(error) else ""
                print(f"{path}: {type(error).__name__}: {message}")
        if invalid:
            raise SystemExit(1)
