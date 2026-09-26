import argparse

from omegaconf import DictConfig, ListConfig, OmegaConf

from omegakit.cli.arguments import split_arguments
from omegakit.loading import load_config
from omegakit.validation import resolve_config


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
        "--node", metavar="KEY", help="print only this node, such as training.model"
    )
    parser.add_argument(
        "--resolve",
        action="store_true",
        help="resolve interpolations; missing values print as ???",
    )
    parser.add_argument(
        "--keep-meta", action="store_true", help="keep $meta keys in the output"
    )
    parser.set_defaults(run=run, parser=parser)


def run(arguments: argparse.Namespace) -> None:
    """Print the config named in `arguments`.

    Args:
        arguments: The parsed `show` arguments.

    Raises:
        SystemExit: With status 1 if the config cannot be loaded, or the node does
            not exist.
    """
    parser: argparse.ArgumentParser = arguments.parser
    paths, overrides = split_arguments(arguments.arguments)
    if len(paths) != 1:
        parser.error("give exactly one config file")
    try:
        config = load_config(
            paths[0], overrides=overrides or None, keep_meta=arguments.keep_meta
        )
    except Exception as error:
        print(f"{paths[0]}: {type(error).__name__}: {str(error).splitlines()[0]}")
        raise SystemExit(1) from error
    node = config
    if arguments.node is not None:
        node = OmegaConf.select(config, arguments.node, default=None)
        if node is None:
            print(f"{paths[0]}: no node `{arguments.node}`")
            raise SystemExit(1)
    if not isinstance(node, (DictConfig, ListConfig)):
        print(node)
        return
    if arguments.resolve:
        node = OmegaConf.create(resolve_config(node, allow_missing=True))
    print(OmegaConf.to_yaml(node), end="")
