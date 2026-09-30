from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import yaml
from omegaconf import DictConfig, ListConfig, Node, OmegaConf
from omegaconf.errors import InterpolationKeyError, OmegaConfBaseException

from .errors import ConfigLoadError, OmegaKitBaseException
from .keys import BASE_KEY, DEFAULTS_KEY, IMPORT_KEY
from .utils import describe_error, describe_value, format_full_key, format_node_path
from .walk import walk, walk_post_order

_NULL_TAG = "tag:yaml.org,2002:null"


def load_file(file_path: Path) -> DictConfig | ListConfig:
    """Load one YAML file.

    Args:
        file_path: The file to load.

    Returns:
        The file's content.

    Raises:
        ConfigLoadError: If the file is not valid YAML or not UTF-8, holds a
            single value instead of a mapping or a list, or holds a value that
            OmegaConf rejects.
        OSError: If the file cannot be read.
    """  # noqa: DOC503
    try:
        # `OmegaConf.load` turns a single string into a mapping and fails on other
        # single values with an `OSError`, so look at the document first.
        document = yaml.compose(file_path.read_text("utf-8"), Loader=yaml.SafeLoader)
        if isinstance(document, yaml.ScalarNode) and document.tag != _NULL_TAG:
            raise ConfigLoadError(
                f"Cannot load `{file_path}`: it holds a single value, not a mapping "
                "or a list."
            )
        return OmegaConf.load(file_path)
    except OmegaKitBaseException:
        raise
    except (yaml.YAMLError, UnicodeDecodeError, OmegaConfBaseException) as error:
        raise ConfigLoadError(
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

    Raises:
        ConfigLoadError: If an import is invalid, cannot be read, leaves
            `import_root`, or forms a cycle.
    """  # noqa: DOC502
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


def select_node(
    config: DictConfig | ListConfig, node_path: str, resolve: bool = False
) -> Node | None:
    """Select a node by a dotted path, such as `items.0.name`, without resolving it.

    Args:
        config: The config to select from.
        node_path: The dotted path from `config`.
        resolve: Follow an interpolation on the way, such as `a` in `a.b` for
            `a: ${other}`. Defaults to `False`.

    Returns:
        The selected node, unresolved, or `None` if there is none at `node_path`.

    Raises:
        ConfigLoadError: If the path goes through an interpolation and `resolve`
            is `False`.
    """
    node: Any = config
    walked: list[str] = []
    for part in filter(None, node_path.split(".")):
        if isinstance(node, Node) and node._is_interpolation():
            if not resolve:
                raise ConfigLoadError(
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

    Args:
        config: The config to process.

    Raises:
        ConfigLoadError: If a `$base` is not a mapping or a list of mappings,
            cannot be resolved, or if `$base` references form a cycle.
    """  # noqa: DOC502
    _merge_in_dependency_order(config, BASE_KEY, _merge_base)


def apply_defaults(config: DictConfig | ListConfig) -> None:
    """Merge every `$defaults` under its dict-valued siblings in place.

    Args:
        config: The config to process.

    Raises:
        ConfigLoadError: If a `$defaults` is not a mapping, cannot be resolved,
            or if `$defaults` references form a cycle.
    """  # noqa: DOC502
    _merge_in_dependency_order(config, DEFAULTS_KEY, _merge_defaults)


def merge_overrides(
    config: DictConfig, overrides: DictConfig | dict[str, Any] | list[str]
) -> None:
    """Merge overrides into a config in place.

    Args:
        config: The config to change.
        overrides: A `DictConfig`, a dictionary, or a list of `key=value` strings.

    Raises:
        ConfigLoadError: If an override does not parse, has a value of an
            unsupported type, or is rejected by `config`.
        TypeError: If `overrides` is not a `DictConfig`, a `dict` or a `list`, or a
            list item is not a string.
    """  # noqa: DOC503
    try:
        parsed_overrides = _parse_overrides(overrides)
        config.merge_with(parsed_overrides)
    except OmegaKitBaseException:
        raise
    except OmegaConfBaseException as error:
        location = f" `{format_full_key(error.full_key)}`" if error.full_key else ""
        raise ConfigLoadError(
            f"Cannot apply the override{location}: {describe_error(error)}"
        ) from error


def strip_keys(config: DictConfig | ListConfig, exclude: set[str]) -> None:
    """Remove the keys in `exclude` from every mapping node of `config` in place.

    Args:
        config: The config to process.
        exclude: The keys to remove, such as `$meta`.
    """
    for node in walk(config):
        for key in list(node.keys()):
            if key in exclude:
                node.pop(key)


def _load_import(
    container: DictConfig | ListConfig,
    key: Any,
    raw_statement: str,
    config_path: Path,
    visited_paths: set[Path],
    cache: dict[Path, DictConfig | ListConfig],
    import_root: Path | None,
) -> Any:
    try:
        statement = container[key]
    except OmegaConfBaseException as error:
        raise ConfigLoadError(
            f"Cannot resolve `{raw_statement}` in `{config_path}`: "
            f"{describe_error(error)}"
        ) from error
    args = statement[len(IMPORT_KEY) :].strip().split("#")
    if len(args) > 2:
        raise ConfigLoadError(
            f"Import `{statement}` in `{config_path}` contains more than one `#`. Use "
            "`#` only to separate the file path from the node path."
        )
    file_path = Path(args[0].strip())
    if not file_path.is_absolute():
        file_path = Path(config_path.parent, file_path)
    file_path = file_path.resolve()
    if import_root is not None and not file_path.is_relative_to(import_root):
        raise ConfigLoadError(
            f"Import `{statement}` in `{config_path}` reads `{file_path}`, which is "
            f"outside the import root `{import_root}`."
        )
    node_path = args[1].strip() if len(args) > 1 else ""
    if file_path in visited_paths:
        raise ConfigLoadError(
            f"Cannot import `{statement}` in `{config_path}`: `{file_path}` is already "
            "being imported, so the imports form a cycle."
        )
    if file_path in cache:
        imported_config = cache[file_path]
    else:
        try:
            imported_config = load_file(file_path)
        except (OSError, ConfigLoadError) as error:
            raise ConfigLoadError(
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
    except ConfigLoadError as error:
        raise ConfigLoadError(
            f"Import `{statement}` in `{config_path}`: {error}"
        ) from error
    if node is None:
        raise ConfigLoadError(
            f"Import `{statement}` in `{config_path}` selects node `{node_path}`, "
            f"which does not exist in `{file_path}`."
        )
    return node


def _merge_in_dependency_order(
    config: DictConfig | ListConfig,
    key: str,
    merge: Callable[[DictConfig, Any], None],
) -> None:
    while True:
        waiting: list[DictConfig] = []
        # The nodes that each waiting node waits for, by `id`: the holders of `key`
        # inside its reference, and for an ancestor, the waiting nodes below it.
        waits_for: dict[int, list[DictConfig]] = {}
        first_error: OmegaConfBaseException | None = None
        merged = False
        for node in list(walk_post_order(config)):
            if node._get_node(key) is None:
                continue
            if id(node) not in waits_for:
                try:
                    value = node[key]
                except InterpolationKeyError as error:
                    if first_error is None:
                        first_error = error
                    waits_for[id(node)] = []
                else:
                    referenced = value if isinstance(value, ListConfig) else [value]
                    holders = [
                        inner
                        for item in referenced
                        if isinstance(item, DictConfig)
                        for inner in walk(item)
                        if inner._get_node(key) is not None
                    ]
                    if not holders:
                        merge(node, value)
                        merged = True
                        continue
                    waits_for[id(node)] = holders
            waiting.append(node)
            # Merging an ancestor replaces its children, so ancestors wait too.
            parent = node._get_parent()
            while parent is not None:
                waits_for.setdefault(id(parent), []).append(node)
                parent = parent._get_parent()
        if not waiting:
            return
        if not merged:
            if first_error is not None:
                raise ConfigLoadError(
                    f"Cannot resolve `{format_full_key(first_error.full_key or key)}`: "
                    f"{describe_error(first_error)}"
                ) from first_error
            nodes = ", ".join(
                f"`{format_node_path(node)}`"
                for node in waiting
                if _waits_for_itself(node, waits_for)
            )
            raise ConfigLoadError(f"`{key}` references form a cycle between {nodes}.")


def _merge_base(node: DictConfig, base: Any) -> None:
    if isinstance(base, ListConfig):
        bases = [base[index] for index in range(len(base))]
        if not all(isinstance(item, DictConfig) for item in bases):
            raise ConfigLoadError(
                f"List-valued `{BASE_KEY}` in `{format_node_path(node)}` must contain "
                "only mappings."
            )
    elif isinstance(base, DictConfig):
        bases = [base]
    else:
        raise ConfigLoadError(
            f"`{BASE_KEY}` in `{format_node_path(node)}` is not a mapping or a list of "
            "mappings."
        )
    node.pop(BASE_KEY)
    merged_config = cast(DictConfig, OmegaConf.merge(*bases, node))
    for key in list(merged_config.keys()):
        node[key] = merged_config._get_node(key)


def _merge_defaults(node: DictConfig, defaults: Any) -> None:
    if not isinstance(defaults, DictConfig):
        raise ConfigLoadError(
            f"`{DEFAULTS_KEY}` in `{format_node_path(node)}` is not a mapping."
        )
    node.pop(DEFAULTS_KEY)
    for key, item in list(node.items_ex(resolve=False)):
        if not str(key).startswith("$") and isinstance(item, DictConfig):
            node[key] = OmegaConf.merge(defaults, item)


def _waits_for_itself(node: DictConfig, waits_for: dict[int, list[DictConfig]]) -> bool:
    seen: set[int] = set()
    pending = list(waits_for[id(node)])
    while pending:
        other = pending.pop()
        if other is node:
            return True
        if id(other) not in seen:
            seen.add(id(other))
            pending.extend(waits_for[id(other)])
    return False


def _parse_overrides(
    overrides: DictConfig | dict[str, Any] | list[str],
) -> DictConfig:
    if isinstance(overrides, DictConfig):
        return overrides
    elif isinstance(overrides, dict):
        return OmegaConf.create(overrides)
    elif isinstance(overrides, list):
        parsed = OmegaConf.create()
        for override in overrides:
            if not isinstance(override, str):
                raise TypeError(
                    "An override in a list must be a `key=value` string, not "
                    f"{describe_value(override)}."
                )
            try:
                parsed.merge_with_dotlist([override])
            except (yaml.YAMLError, OmegaConfBaseException) as error:
                raise ConfigLoadError(
                    f"Cannot parse the override `{override}`: {describe_error(error)}"
                ) from error
        return parsed
    else:
        raise TypeError(
            "`overrides` must be a `DictConfig`, a `dict` or a `list` of `key=value` "
            f"strings, not `{type(overrides).__name__}`."
        )
