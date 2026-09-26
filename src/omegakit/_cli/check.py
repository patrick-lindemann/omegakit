import argparse
from pathlib import Path

from omegakit._cli.arguments import split_arguments
from omegakit._loading import load_config
from omegakit._utils import import_object
from omegakit._validation import validate


def register(commands: argparse._SubParsersAction) -> None:
    """Add the `check` command.

    Args:
        commands: The subcommands of the `omegakit` parser.
    """
    parser = commands.add_parser(
        "check",
        help="load and validate config files without building anything",
        description="Load and validate config files without building anything. "
        "Prints one line per invalid file and exits with 1 if any is invalid.",
    )
    parser.add_argument(
        "arguments",
        nargs="+",
        metavar="CONFIG_OR_OVERRIDE",
        help="config files, and key=value overrides applied to every file",
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
    parser.set_defaults(run=run, parser=parser)


def run(arguments: argparse.Namespace) -> None:
    """Check the config files named in `arguments`.

    Args:
        arguments: The parsed `check` arguments.

    Raises:
        SystemExit: With status 1 if a file is invalid.
    """
    parser: argparse.ArgumentParser = arguments.parser
    paths, overrides = split_arguments(arguments.arguments)
    if not paths:
        parser.error("no config file given")
    if arguments.import_root is not None and not arguments.import_root.is_dir():
        parser.error(f"--import-root {arguments.import_root} is not a directory")
    schema = None
    if arguments.schema is not None:
        try:
            schema = import_object(arguments.schema)
        except ImportError as error:
            parser.error(f"cannot import --schema: {error}")
    invalid = 0
    for path in paths:
        try:
            config = load_config(
                path, overrides=overrides or None, import_root=arguments.import_root
            )
            validate(
                config,
                schema=schema,
                allow_missing=arguments.allow_missing,
                allowed_modules=arguments.allowed_modules,
            )
        # A module that exits while it is imported must not pass the check.
        except (Exception, SystemExit) as error:
            invalid += 1
            message = str(error).splitlines()[0] if str(error) else ""
            print(f"{path}: {type(error).__name__}: {message}")
    if invalid:
        raise SystemExit(1)
