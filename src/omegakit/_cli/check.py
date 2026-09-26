import argparse

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
    schema = None
    if arguments.schema is not None:
        try:
            schema = import_object(arguments.schema)
        except (ImportError, ValueError) as error:
            parser.error(f"cannot import --schema: {error}")
    invalid = 0
    for path in paths:
        try:
            config = load_config(path, overrides=overrides or None)
            validate(config, schema=schema, allow_missing=arguments.allow_missing)
        except Exception as error:
            invalid += 1
            message = str(error).splitlines()[0] if str(error) else ""
            print(f"{path}: {type(error).__name__}: {message}")
    if invalid:
        raise SystemExit(1)
