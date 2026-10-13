from argparse import ArgumentError, ArgumentParser
from pathlib import Path
from typing import Any, NoReturn, override

from omegaconf import DictConfig, ListConfig, OmegaConf

from omegakit._core.resolve import resolve_item
from omegakit.load import load_config

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
            help="print only this node, selected as OmegaConf.select does, such as "
            "training.model or items[0]",
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
            help="print the values of ${secret:...} instead of ***",
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
            value = (
                _to_plain(node, args.resolve)
                if isinstance(node, (DictConfig, ListConfig))
                else node
            )
        except Exception as error:
            _fail(args.config, error)
        if isinstance(value, (DictConfig, ListConfig, dict, list)):
            print(OmegaConf.to_yaml(value), end="")
        else:
            print("null" if value is None else value)


def _fail(path: Path, error: Exception) -> NoReturn:
    message = str(error).splitlines()[0] if str(error) else ""
    print(f"{path}: {type(error).__name__}: {message}")
    raise SystemExit(1) from error


def _to_plain(node: Any, resolve: bool) -> Any:
    if isinstance(node, (DictConfig, ListConfig)) and not (
        node._is_missing() or node._is_interpolation()
    ):
        if isinstance(node, ListConfig):
            return list(_to_plain_items(node, resolve).values())
        return _to_plain_items(node, resolve)
    if not resolve:
        return node._value()
    return resolve_item(node._get_parent_container(), node._key())


def _to_plain_items(
    container: DictConfig | ListConfig, resolve: bool
) -> dict[Any, Any]:
    keys: Any = (
        range(len(container)) if isinstance(container, ListConfig) else container
    )
    return {key: _to_plain(container._get_node(key), resolve) for key in keys}


def _mask_secret(_: Any) -> str:
    return "***"
