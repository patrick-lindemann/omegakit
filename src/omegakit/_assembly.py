from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import yaml
from omegaconf import DictConfig, ListConfig, Node, OmegaConf
from omegaconf.errors import InterpolationKeyError, OmegaConfBaseException

from ._keys import BASE_KEY, DEFAULTS_KEY, IMPORT_KEY
from ._schema import ConfigValidationError
from ._utils import describe_error, walk, walk_post_order

_NULL_TAG = "tag:yaml.org,2002:null"


def load_file(file_path: Path) -> DictConfig | ListConfig:
    """Load one YAML file.

    Args:
        file_path: The file to load.

    Returns:
        The file's content.

    Raises:
        ConfigValidationError: If the file is not valid YAML or not UTF-8, holds a
            single value instead of a mapping or a list, or holds a value that
            OmegaConf rejects.
    """
    try:
        # `OmegaConf.load` turns a single string into a mapping and fails on other
        # single values with an `OSError`, so look at the document first.
        document = yaml.compose(file_path.read_text("utf-8"), Loader=yaml.SafeLoader)
        if isinstance(document, yaml.ScalarNode) and document.tag != _NULL_TAG:
            raise ConfigValidationError(
                f"Cannot load `{file_path}`: it holds a single value, not a mapping "
                "or a list."
            )
        return OmegaConf.load(file_path)
    except (yaml.YAMLError, UnicodeDecodeError, OmegaConfBaseException) as error:
        raise ConfigValidationError(
            f"Cannot load `{file_path}`: {describe_error(error)}"
        ) from error


def resolve_imports(
    config: DictConfig | ListConfig,
    config_path: Path,
    visited_paths: set[Path],
    cache: dict[Path, DictConfig | ListConfig],
    import_root: Path | None,
) -> None:
    """Replace every `~import` value in `config` in place, depth-first.

    Args:
        config: The config to process.
        config_path: The file `config` was loaded from; relative imports resolve
            against its directory.
        visited_paths: The files in the current import chain, for cycle detection.
        cache: Imported files already loaded during this `load_config` call.
        import_root: The resolved directory that every imported file must be in, or
            `None` for no restriction.
    """
    if isinstance(config, ListConfig):
        for index in range(len(config)):
            node = config._get_node(index)
            if isinstance(node, (DictConfig, ListConfig)):
                resolve_imports(node, config_path, visited_paths, cache, import_root)
            else:
                value = node._value() if isinstance(node, Node) else None
                if isinstance(value, str) and value.startswith(IMPORT_KEY):
                    config[index] = _load_import(
                        config,
                        index,
                        value,
                        config_path,
                        visited_paths,
                        cache,
                        import_root,
                    )
        return
    for key, value in config.items_ex(resolve=False):
        if isinstance(value, (DictConfig, ListConfig)):
            resolve_imports(value, config_path, visited_paths, cache, import_root)
        elif isinstance(value, str) and value.startswith(IMPORT_KEY):
            config[key] = _load_import(
                config, key, value, config_path, visited_paths, cache, import_root
            )


def _load_import(
    container: DictConfig | ListConfig,
    key: Any,
    statement: str,
    config_path: Path,
    visited_paths: set[Path],
    cache: dict[Path, DictConfig | ListConfig],
    import_root: Path | None,
) -> Any:
    try:
        statement = container[key]
    except OmegaConfBaseException as error:
        raise ConfigValidationError(
            f"Cannot resolve `{statement}` in `{config_path}`: "
            f"{str(error).splitlines()[0]}"
        ) from error
    args = statement[len(IMPORT_KEY) :].strip().split("#")
    if len(args) > 2:
        raise ConfigValidationError(
            f"Import `{statement}` in `{config_path}` contains more than one `#`. Use "
            "`#` only to separate the file path from the node path."
        )
    file_path = Path(args[0].strip())
    if not file_path.is_absolute():
        file_path = Path(config_path.parent, file_path)
    file_path = file_path.resolve()
    if import_root is not None and not file_path.is_relative_to(import_root):
        raise ConfigValidationError(
            f"Import `{statement}` in `{config_path}` reads `{file_path}`, which is "
            f"outside the import root `{import_root}`."
        )
    node_path = args[1].strip() if len(args) > 1 else ""
    if file_path in visited_paths:
        raise ConfigValidationError(
            f"Circular import detected: `{statement}` in `{config_path}` imports "
            f"`{file_path}`, which was already imported."
        )
    if file_path in cache:
        imported_config = cache[file_path]
    else:
        try:
            imported_config = load_file(file_path)
        except (OSError, ConfigValidationError) as error:
            raise ConfigValidationError(
                f"Cannot import `{statement}` in `{config_path}`: {error}"
            ) from error
        resolve_imports(
            imported_config,
            file_path,
            visited_paths={*visited_paths, file_path},
            cache=cache,
            import_root=import_root,
        )
        cache[file_path] = imported_config
    try:
        node = select_node(imported_config, node_path)
    except ConfigValidationError as error:
        raise ConfigValidationError(
            f"Import `{statement}` in `{config_path}`: {error}"
        ) from error
    if node is None:
        raise ConfigValidationError(
            f"Import `{statement}` in `{config_path}` selects node `{node_path}`, "
            f"which does not exist in `{file_path}`."
        )
    return node


def select_node(
    config: DictConfig | ListConfig, node_path: str, *, resolve: bool = False
) -> Node | None:
    """Select a node by a dotted path, such as `items.0.name`, without resolving it.

    A segment selects a key in a mapping or an integer index in a list, where a
    negative index counts from the end. An empty path selects `config`.

    Args:
        config: The config to select from.
        node_path: The dotted path from `config`.
        resolve: Follow an interpolation on the way, such as `a` in `a.b` for
            `a: ${other}`. Defaults to `False`.

    Returns:
        The selected node, unresolved, or `None` if there is none at `node_path`.

    Raises:
        ConfigValidationError: If the path goes through an interpolation and
            `resolve` is `False`.
    """
    node: Any = config
    walked: list[str] = []
    for part in filter(None, node_path.split(".")):
        if isinstance(node, Node) and node._is_interpolation():
            if not resolve:
                raise ConfigValidationError(
                    f"Node path `{node_path}` goes through `{'.'.join(walked)}`, "
                    "which is an interpolation."
                )
            node = cast(Any, node._get_parent_container())[node._key()]
        if isinstance(node, DictConfig):
            node = node._get_node(part)
        elif (
            isinstance(node, ListConfig)
            and part.lstrip("-").isdigit()
            and -len(node) <= int(part) < len(node)
        ):
            node = node._get_node(int(part))
        else:
            return None
        if node is None:
            return None
        walked.append(part)
    return node


def merge_bases(config: DictConfig | ListConfig) -> None:
    """Merge every `$base` underneath its node in place, in dependency order.

    Children are merged before parents, and a node whose `$base` refers to a node that
    still has an unmerged `$base` waits until that node is merged.

    Args:
        config: The config to process.

    Raises:
        ConfigValidationError: If a `$base` is not a mapping or a list of mappings,
            cannot be resolved, or if `$base` references form a cycle.
    """
    cycle = _merge_in_dependency_order(config, BASE_KEY, _merge_base)
    if cycle:
        nodes = ", ".join(f"`{_node_path(node)}`" for node in cycle)
        raise ConfigValidationError(
            f"`{BASE_KEY}` references form a cycle between {nodes}."
        )


def apply_defaults(config: DictConfig | ListConfig) -> None:
    """Merge every `$defaults` under its dict-valued siblings in place.

    Nested mappings are processed before their parents, and a `$defaults` that refers
    to a node with an unapplied `$defaults` waits until that node is processed.

    Args:
        config: The config to process.

    Raises:
        ConfigValidationError: If a `$defaults` is not a mapping, cannot be resolved,
            or if `$defaults` references form a cycle.
    """
    cycle = _merge_in_dependency_order(config, DEFAULTS_KEY, _merge_defaults)
    if cycle:
        nodes = ", ".join(f"`{_node_path(node)}`" for node in cycle)
        raise ConfigValidationError(
            f"`{DEFAULTS_KEY}` references form a cycle between {nodes}."
        )


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


def _merge_in_dependency_order(
    config: DictConfig | ListConfig,
    key: str,
    merge: Callable[[DictConfig, Any], None],
) -> list[DictConfig]:
    """Merge every node that holds `key`, children first, in dependency order.

    A node waits while its value refers to a node that still holds `key`, or to a key
    that does not exist yet. Ancestors of a waiting node wait too, because merging
    replaces their children. Passes repeat until nothing waits. A pass without
    progress is a cycle, or a reference that will never resolve.

    Args:
        config: The config to process.
        key: `$base` or `$defaults`.
        merge: Merges a node's value of `key` into the node.

    Returns:
        The nodes that still wait after a pass without progress, which form a cycle,
        or an empty list once everything is merged.

    Raises:
        ConfigValidationError: If a value refers to a key that never appears.
    """
    while True:
        waiting: list[DictConfig] = []
        blocked: set[int] = set()
        first_error: OmegaConfBaseException | None = None
        merged = False
        for node in list(walk_post_order(config)):
            if node._get_node(key) is None:
                continue
            if id(node) not in blocked:
                try:
                    value = node[key]
                except InterpolationKeyError as error:
                    if first_error is None:
                        first_error = error
                else:
                    referenced = value if isinstance(value, ListConfig) else [value]
                    if not any(
                        isinstance(item, DictConfig)
                        and any(
                            inner._get_node(key) is not None for inner in walk(item)
                        )
                        for item in referenced
                    ):
                        merge(node, value)
                        merged = True
                        continue
            waiting.append(node)
            parent = node._get_parent()
            while parent is not None and id(parent) not in blocked:
                blocked.add(id(parent))
                parent = parent._get_parent()
        if not waiting:
            return []
        if not merged:
            if first_error is not None:
                raise ConfigValidationError(
                    f"Cannot resolve `{first_error.full_key or key}`: "
                    f"{str(first_error).splitlines()[0]}"
                ) from first_error
            return waiting


def _merge_base(node: DictConfig, base: Any) -> None:
    # A base may be a single mapping or a list of mappings. Later list elements take
    # precedence over earlier ones, and the node's own keys over all.
    if isinstance(base, ListConfig):
        bases = [base[index] for index in range(len(base))]
        if not all(isinstance(item, DictConfig) for item in bases):
            raise ConfigValidationError(
                f"List-valued `{BASE_KEY}` in `{_node_path(node)}` must contain only "
                "dictionaries."
            )
    elif isinstance(base, DictConfig):
        bases = [base]
    else:
        raise ConfigValidationError(
            f"`{BASE_KEY}` in `{_node_path(node)}` is not a dictionary or a list of "
            "dictionaries."
        )
    node.pop(BASE_KEY)
    merged_config = cast(DictConfig, OmegaConf.merge(*bases, node))
    for key in list(merged_config.keys()):
        node[key] = merged_config._get_node(key)


def _merge_defaults(node: DictConfig, defaults: Any) -> None:
    if not isinstance(defaults, DictConfig):
        raise ConfigValidationError(
            f"`{DEFAULTS_KEY}` in `{_node_path(node)}` is not a dictionary."
        )
    node.pop(DEFAULTS_KEY)
    for key in list(node.keys()):
        if str(key).startswith("$"):
            continue
        item = node._get_node(key)
        if isinstance(item, DictConfig):
            node[key] = OmegaConf.merge(defaults, item)


def _node_path(node: DictConfig) -> str:
    return node._get_full_key(None) or "<root>"
