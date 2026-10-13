from argparse import ArgumentError, ArgumentParser
from pathlib import Path
from typing import Any, NoReturn, override

from omegaconf import DictConfig, ListConfig, OmegaConf

from omegakit._core.load import load_config

from ._args import Arguments
from ._routine import Routine

_NOT_FOUND = object()


class ShowArguments(Arguments):
    """The parsed arguments of the `show` command."""

    config: Path
    overrides: list[str] | None
    node: str | None
    resolve: bool
    keep_meta: bool
    show_secrets: bool
    include_root: Path | None


class ShowRoutine(Routine[ShowArguments]):
    """The `show` command, which prints a config as `load_config` assembles it."""

    name = "show"
    help = "print a config as assembled by load_config"
    description = "Print a config after includes, bases, $each and overrides."

    @override
    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "config",
            type=Path,
            help="the config file",
        )
        parser.add_argument(
            "--overrides",
            action="extend",
            nargs="+",
            metavar="KEY=VALUE",
            help="set values, such as seed=3",
        )
        parser.add_argument(
            "--node",
            metavar="KEY",
            help="print only this node, selected as OmegaConf.select does, such as "
            "training.model or items[0]",
        )
        parser.add_argument(
            "--resolve",
            action="store_true",
            help="resolve interpolations (only in the selected node, with --node)",
        )
        parser.add_argument(
            "--keep-meta", action="store_true", help="keep $meta keys in the output"
        )
        parser.add_argument(
            "--show-secrets",
            action="store_true",
            help="print the values of ${secret:...} instead of ***",
        )
        parser.add_argument(
            "--include-root",
            type=Path,
            metavar="DIR",
            help="reject any ~include of a file outside DIR",
        )

    @override
    def run(self, args: ShowArguments) -> None:
        """Print the config named in `args`.

        Args:
            args: The parsed `show` arguments.

        Raises:
            ArgumentError: If `--include-root` is not a directory.
            SystemExit: With status 1 if the config cannot be loaded or resolved, or
                the node does not exist.
        """
        if args.include_root is not None and not args.include_root.is_dir():
            raise ArgumentError(
                None, f"--include-root {args.include_root} is not a directory"
            )
        try:
            config = load_config(
                args.config,
                overrides=args.overrides,
                keep_meta=args.keep_meta,
                include_root=args.include_root,
            )
        except Exception as error:
            _fail(args.config, error)
        if not args.show_secrets:
            # Every value built from a secret then holds `***`, also a single value
            # that --node selects, which OmegaConf resolves. Loading resolved with the
            # real values, and the config caches what its resolvers gave.
            OmegaConf.register_resolver("secret", _mask_secret, replace=True)
            OmegaConf.clear_cache(config)
        try:
            node = config
            if args.node is not None:
                node = OmegaConf.select(config, args.node, default=_NOT_FOUND)
            if node is _NOT_FOUND:
                print(f"{args.config}: no node `{args.node}`")
                raise SystemExit(1)
            if isinstance(node, (DictConfig, ListConfig)):
                text = OmegaConf.to_yaml(node, resolve=args.resolve)
            else:
                text = "null\n" if node is None else f"{node}\n"
        except Exception as error:
            _fail(args.config, error)
        print(text, end="")


def _fail(path: Path, error: Exception) -> NoReturn:
    message = str(error).splitlines()[0] if str(error) else ""
    print(f"{path}: {type(error).__name__}: {message}")
    raise SystemExit(1) from error


def _mask_secret(_: Any) -> str:
    return "***"
