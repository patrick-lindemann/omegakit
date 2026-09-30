from pathlib import Path
from typing import Any, cast

import yaml
from omegaconf import DictConfig, ListConfig, Node, OmegaConf
from omegaconf.errors import OmegaConfBaseException

from .errors import ConfigLoadError, OmegaKitBaseException
from .keys import BASE_KEY, DEFAULTS_KEY, IMPORT_KEY
from .tree import load_file, merge_in_dependency_order, select_node
from .utils import describe_error, describe_value, format_full_key, format_node_path


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


def merge_bases(config: DictConfig | ListConfig) -> None:
    """Merge every `$base` underneath its node in place, in dependency order.

    Args:
        config: The config to process.

    Raises:
        ConfigLoadError: If a `$base` is not a mapping or a list of mappings,
            cannot be resolved, or if `$base` references form a cycle.
    """  # noqa: DOC502
    merge_in_dependency_order(config, BASE_KEY, _merge_base)


def apply_defaults(config: DictConfig | ListConfig) -> None:
    """Merge every `$defaults` under its dict-valued siblings in place.

    Args:
        config: The config to process.

    Raises:
        ConfigLoadError: If a `$defaults` is not a mapping, cannot be resolved,
            or if `$defaults` references form a cycle.
    """  # noqa: DOC502
    merge_in_dependency_order(config, DEFAULTS_KEY, _merge_defaults)


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
