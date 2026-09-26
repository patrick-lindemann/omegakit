import argparse
from pathlib import Path
from typing import NoReturn

from omegaconf import DictConfig, ListConfig, OmegaConf

from omegakit._assembly import select_node
from omegakit._cli.arguments import split_arguments
from omegakit._loading import load_config
from omegakit._validation import resolve_config, resolve_item


def register(commands: argparse._SubParsersAction) -> None:
    """Add the `show` command.

    Args:
        commands: The subcommands of the `omegakit` parser.
    """
    parser = commands.add_parser(
        "show",
        help="print a config as assembled by load_config",
        description="Print a config after imports, bases, defaults and overrides.",
    )
    parser.add_argument(
        "arguments",
        nargs="+",
        metavar="CONFIG_OR_OVERRIDE",
        help="one config file, and key=value overrides",
    )
    parser.add_argument(
        "--node",
        metavar="KEY",
        help="print only this node, such as training.model or items.0; it is not "
        "resolved unless --resolve is given",
    )
    parser.add_argument(
        "--resolve",
        action="store_true",
        help="resolve interpolations (only in the selected node, with --node); "
        "missing values print as ???",
    )
    parser.add_argument(
        "--keep-meta", action="store_true", help="keep $meta keys in the output"
    )
    parser.add_argument(
        "--import-root",
        type=Path,
        metavar="DIR",
        help="reject any ~import of a file outside DIR",
    )
    parser.set_defaults(run=run, parser=parser)


def run(arguments: argparse.Namespace) -> None:
    """Print the config named in `arguments`.

    Args:
        arguments: The parsed `show` arguments.

    Raises:
        SystemExit: With status 1 if the config cannot be loaded or resolved, or the
            node does not exist.
    """
    parser: argparse.ArgumentParser = arguments.parser
    paths, overrides = split_arguments(arguments.arguments)
    if len(paths) != 1:
        parser.error("give exactly one config file")
    if arguments.import_root is not None and not arguments.import_root.is_dir():
        parser.error(f"--import-root {arguments.import_root} is not a directory")
    try:
        config = load_config(
            paths[0],
            overrides=overrides or None,
            keep_meta=arguments.keep_meta,
            import_root=arguments.import_root,
        )
    except Exception as error:
        _fail(paths[0], error)
    try:
        node = config
        if arguments.node is not None:
            node = select_node(config, arguments.node, resolve=arguments.resolve)
        if node is None:
            print(f"{paths[0]}: no node `{arguments.node}`")
            raise SystemExit(1)
        if isinstance(node, (DictConfig, ListConfig)):
            value = (
                resolve_config(node, allow_missing=True) if arguments.resolve else node
            )
        elif arguments.resolve:
            value = resolve_item(node._get_parent_container(), node._key())
        else:
            value = node._value()
    except Exception as error:
        # Without --resolve, the only error here is a path through an interpolation.
        _fail(
            paths[0], error, "" if arguments.resolve else " Add --resolve to follow it."
        )
    if isinstance(value, (DictConfig, ListConfig, dict, list)):
        print(OmegaConf.to_yaml(value), end="")
    else:
        print("null" if value is None else value)


def _fail(path: Path, error: Exception, hint: str = "") -> NoReturn:
    message = str(error).splitlines()[0] if str(error) else ""
    print(f"{path}: {type(error).__name__}: {message}{hint}")
    raise SystemExit(1) from error
