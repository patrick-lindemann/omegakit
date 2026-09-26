from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any, cast

from omegaconf import DictConfig, ListConfig, Node, OmegaConf

from .keys import BASE_KEY, DEFAULTS_KEY, IMPORT_KEY
from .utils import walk


def resolve_imports(
    config: DictConfig | ListConfig,
    config_path: Path,
    visited_paths: set[Path],
    cache: dict[Path, DictConfig | ListConfig],
) -> None:
    """Replace every `~import` value in `config` in place, depth-first.

    Args:
        config: The config to process.
        config_path: The file `config` was loaded from; relative imports resolve
            against its directory.
        visited_paths: The files in the current import chain, for cycle detection.
        cache: Imported files already loaded during this `load_config` call.
    """
    if isinstance(config, ListConfig):
        for index in range(len(config)):
            node = config._get_node(index)
            if isinstance(node, (DictConfig, ListConfig)):
                resolve_imports(node, config_path, visited_paths, cache)
            else:
                value = node._value() if isinstance(node, Node) else None
                if isinstance(value, str) and value.startswith(IMPORT_KEY):
                    config[index] = _load_import(
                        config[index], config_path, visited_paths, cache
                    )
        return
    for key, value in config.items_ex(resolve=False):
        if isinstance(value, (DictConfig, ListConfig)):
            resolve_imports(value, config_path, visited_paths, cache)
        elif isinstance(value, str) and value.startswith(IMPORT_KEY):
            config[key] = _load_import(config[key], config_path, visited_paths, cache)


def _load_import(
    statement: str,
    config_path: Path,
    visited_paths: set[Path],
    cache: dict[Path, DictConfig | ListConfig],
) -> Any:
    # Match the pattern ~import <file_path>[#<node_path>]
    args = statement[len(IMPORT_KEY) :].strip().split("#")
    if len(args) > 2:
        raise ValueError(
            f"Import `{statement}` contains more than one `#`. Use `#` only to "
            "separate the file path from the node path."
        )
    file_path = Path(args[0])
    if not file_path.is_absolute():
        file_path = Path(config_path.parent, file_path)
    file_path = file_path.resolve()
    node_path = args[1].strip() if len(args) > 1 else ""
    # Load the imported config file and resolve its own imports first
    if file_path in visited_paths:
        raise ValueError(
            f"Circular import detected: `{file_path}` was already imported."
        )
    if file_path in cache:
        imported_config = cache[file_path]
    else:
        imported_config = OmegaConf.load(file_path)
        resolve_imports(
            imported_config,
            file_path,
            visited_paths={*visited_paths, file_path},
            cache=cache,
        )
        cache[file_path] = imported_config
    node = imported_config
    for part in filter(None, node_path.split(".")):
        if isinstance(node, DictConfig):
            node = node._get_node(part)
        elif (
            isinstance(node, ListConfig)
            and part.lstrip("-").isdigit()
            and -len(node) <= int(part) < len(node)
        ):
            node = node._get_node(int(part))
        else:
            node = None
        if node is None:
            break
    if node is None:
        raise ValueError(
            f"Import `{statement}` selects node `{node_path}`, which does not exist in "
            f"`{file_path}`."
        )
    return node


def merge_bases(config: DictConfig | ListConfig) -> None:
    """Merge every `$base` underneath its node in place, children before parents.

    Args:
        config: The config to process.

    Raises:
        ValueError: If a `$base` is not a mapping or a list of mappings.
    """
    for node in _walk_post_order(config):
        if node._get_node(BASE_KEY) is None:
            continue
        base = node[BASE_KEY]
        # A base may be a single mapping or a list of mappings. Later list elements
        # take precedence over earlier ones, and the node's own keys over all.
        if isinstance(base, ListConfig):
            bases = [base[index] for index in range(len(base))]
            if not all(isinstance(item, DictConfig) for item in bases):
                raise ValueError(
                    f"List-valued `{BASE_KEY}` in parent `{node}` must contain only "
                    f"dictionaries."
                )
        elif isinstance(base, DictConfig):
            bases = [base]
        else:
            raise ValueError(
                f"Node `{BASE_KEY}` in parent `{node}` is not a dictionary or a list "
                f"of dictionaries."
            )
        node.pop(BASE_KEY)
        merged_config = cast(DictConfig, OmegaConf.merge(*bases, node))
        for key in list(merged_config.keys()):
            node[key] = merged_config._get_node(key)


def apply_defaults(config: DictConfig | ListConfig) -> None:
    """Merge every `$defaults` under its dict-valued siblings in place.

    Nested mappings are processed before their parents.

    Args:
        config: The config to process.

    Raises:
        ValueError: If a `$defaults` is not a mapping.
    """
    for node in _walk_post_order(config):
        if node._get_node(DEFAULTS_KEY) is None:
            continue
        defaults = node[DEFAULTS_KEY]
        if not isinstance(defaults, DictConfig):
            raise ValueError(
                f"Node `{DEFAULTS_KEY}` in parent `{node}` is not a dictionary."
            )
        node.pop(DEFAULTS_KEY)
        for key in list(node.keys()):
            if str(key).startswith("$"):
                continue
            item = node._get_node(key)
            if isinstance(item, DictConfig):
                node[key] = OmegaConf.merge(defaults, item)


def strip_keys(config: DictConfig | ListConfig, exclude: set[str]) -> None:
    """Remove the given keys from every mapping in `config`, in place.

    Args:
        config: The config to process.
        exclude: The keys to remove.
    """
    for node in walk(config):
        for key in list(node.keys()):
            if key in exclude:
                node.pop(key)


def _walk_post_order(config: DictConfig | ListConfig) -> Iterator[DictConfig]:
    # Like `walk`, but children before parents, so a pass sees assembled children.
    if isinstance(config, DictConfig):
        children = [node for _, node in config.items_ex(resolve=False)]
    else:
        children = [config._get_node(index) for index in range(len(config))]
    for node in children:
        if isinstance(node, (DictConfig, ListConfig)):
            yield from _walk_post_order(node)
    if isinstance(config, DictConfig):
        yield config
