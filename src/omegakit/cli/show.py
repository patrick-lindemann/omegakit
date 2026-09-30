from argparse import ArgumentError, ArgumentParser
from pathlib import Path
from typing import Any, NoReturn, override

from omegaconf import DictConfig, ListConfig, OmegaConf

from omegakit.core.assembly import select_node
from omegakit.core.load import load_config
from omegakit.core.validate import resolve_item
from omegakit.resolvers import register_resolver

from ._args import Arguments
from ._routine import Routine


class ShowArguments(Arguments):
    """The parsed arguments of the `show` command."""

    config: Path
    overrides: list[str] | None
    node: str | None
    resolve: bool
    keep_meta: bool
    show_secrets: bool
    import_root: Path | None


class ShowRoutine(Routine[ShowArguments]):
    """The `show` command, which prints a config as `load_config` assembles it."""

    name = "show"
    help = "print a config as assembled by load_config"
    description = "Print a config after imports, bases, defaults and overrides."

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
            "--show-secrets",
            action="store_true",
            help="with --resolve, print the values of ${secret:...} instead of ***",
        )
        parser.add_argument(
            "--import-root",
            type=Path,
            metavar="DIR",
            help="reject any ~import of a file outside DIR",
        )

    @override
    def run(self, args: ShowArguments) -> None:
        """Print the config named in `args`.

        Args:
            args: The parsed `show` arguments.

        Raises:
            ArgumentError: If `--import-root` is not a directory.
            SystemExit: With status 1 if the config cannot be loaded or resolved, or
                the node does not exist.
        """
        if args.import_root is not None and not args.import_root.is_dir():
            raise ArgumentError(
                None, f"--import-root {args.import_root} is not a directory"
            )
        try:
            config = load_config(
                args.config,
                overrides=args.overrides,
                keep_meta=args.keep_meta,
                import_root=args.import_root,
            )
        except Exception as error:
            _fail(args.config, error)
        if args.resolve and not args.show_secrets:
            # Every value built from a secret then holds `***`. Loading resolved with
            # the real values, and the config caches what its resolvers gave.
            register_resolver("secret", _mask_secret, replace=True)
            OmegaConf.clear_cache(config)
        try:
            node = config
            if args.node is not None:
                node = select_node(config, args.node, resolve=args.resolve)
            if node is None:
                print(f"{args.config}: no node `{args.node}`")
                raise SystemExit(1)
            value = _plain(node, args.resolve)
        except Exception as error:
            # Without --resolve, the only error here is a path through an
            # interpolation.
            _fail(
                args.config,
                error,
                "" if args.resolve else " Add --resolve to follow it.",
            )
        if isinstance(value, (DictConfig, ListConfig, dict, list)):
            print(OmegaConf.to_yaml(value), end="")
        else:
            print("null" if value is None else value)


def _fail(path: Path, error: Exception, hint: str = "") -> NoReturn:
    message = str(error).splitlines()[0] if str(error) else ""
    print(f"{path}: {type(error).__name__}: {message}{hint}")
    raise SystemExit(1) from error


def _plain(node: Any, resolve: bool) -> Any:
    if isinstance(node, (DictConfig, ListConfig)) and not (
        node._is_missing() or node._is_interpolation()
    ):
        if isinstance(node, ListConfig):
            return list(_items(node, resolve).values())
        return _items(node, resolve)
    if not resolve:
        return node._value()
    return resolve_item(node._get_parent_container(), node._key())


def _items(container: DictConfig | ListConfig, resolve: bool) -> dict[Any, Any]:
    keys: Any = (
        range(len(container)) if isinstance(container, ListConfig) else container
    )
    return {key: _plain(container._get_node(key), resolve) for key in keys}


def _mask_secret(_: Any) -> str:
    return "***"
