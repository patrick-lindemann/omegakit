from pathlib import Path
from typing import Any, cast

import yaml
from omegaconf import DictConfig, ListConfig, Node, OmegaConf
from omegaconf.errors import OmegaConfBaseException

from .errors import ConfigLoadError, OmegaKitBaseException, describe_error
from .keys import IMPORT_KEY

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
