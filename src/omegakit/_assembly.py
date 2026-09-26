from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any, cast

from omegaconf import DictConfig, ListConfig, Node, OmegaConf
from omegaconf.errors import InterpolationKeyError, OmegaConfBaseException

from ._keys import BASE_KEY, DEFAULTS_KEY, IMPORT_KEY
from ._utils import walk


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
    """Merge every `$base` underneath its node in place, in dependency order.

    Children are merged before parents, and a node whose `$base` refers to a node that
    still has an unmerged `$base` waits until that node is merged.

    Args:
        config: The config to process.

    Raises:
        ValueError: If a `$base` is not a mapping or a list of mappings, or if `$base`
            references form a cycle.
    """
    cycle = _merge_in_dependency_order(config, BASE_KEY, _merge_base)
    if cycle:
        raise ValueError(f"`{BASE_KEY}` references form a cycle between {cycle}.")


def apply_defaults(config: DictConfig | ListConfig) -> None:
    """Merge every `$defaults` under its dict-valued siblings in place.

    Nested mappings are processed before their parents, and a `$defaults` that refers
    to a node with an unapplied `$defaults` waits until that node is processed.

    Args:
        config: The config to process.

    Raises:
        ValueError: If a `$defaults` is not a mapping, or if `$defaults` references
            form a cycle.
    """
    cycle = _merge_in_dependency_order(config, DEFAULTS_KEY, _merge_defaults)
    if cycle:
        raise ValueError(f"`{DEFAULTS_KEY}` references form a cycle between {cycle}.")


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


def _merge_in_dependency_order(
    config: DictConfig | ListConfig,
    key: str,
    merge: Callable[[DictConfig, Any], None],
) -> str:
    # Returns the nodes that form a cycle, or "" once everything is merged. A node
    # waits while its value refers to a node that still holds `key`, or to a key that
    # does not exist yet. Ancestors of a waiting node wait too, because merging
    # replaces their children. A pass without progress is a cycle, or a reference
    # that will never resolve.
    while True:
        waiting: list[DictConfig] = []
        first_error: OmegaConfBaseException | None = None
        merged = False
        for node in _walk_post_order(config):
            if node._get_node(key) is None:
                continue
            if any(_is_ancestor(node, other) for other in waiting):
                waiting.append(node)
                continue
            try:
                value = node[key]
                referenced = (
                    [value] if not isinstance(value, ListConfig) else list(value)
                )
            except InterpolationKeyError as error:
                first_error = first_error or error
                waiting.append(node)
                continue
            if any(
                isinstance(item, DictConfig)
                and any(inner._get_node(key) is not None for inner in walk(item))
                for item in referenced
            ):
                waiting.append(node)
                continue
            merge(node, value)
            merged = True
        if not waiting:
            return ""
        if not merged:
            if first_error is not None:
                raise first_error
            return ", ".join(f"`{node._get_full_key(None)}`" for node in waiting)


def _merge_base(node: DictConfig, base: Any) -> None:
    # A base may be a single mapping or a list of mappings. Later list elements take
    # precedence over earlier ones, and the node's own keys over all.
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
            f"Node `{BASE_KEY}` in parent `{node}` is not a dictionary or a list of "
            f"dictionaries."
        )
    node.pop(BASE_KEY)
    merged_config = cast(DictConfig, OmegaConf.merge(*bases, node))
    for key in list(merged_config.keys()):
        node[key] = merged_config._get_node(key)


def _merge_defaults(node: DictConfig, defaults: Any) -> None:
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


def _is_ancestor(node: DictConfig, other: DictConfig) -> bool:
    parent = other._get_parent()
    while parent is not None:
        if parent is node:
            return True
        parent = parent._get_parent()
    return False
