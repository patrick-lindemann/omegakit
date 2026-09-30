from pathlib import Path
from typing import Any

from omegaconf import DictConfig, ListConfig, Node
from omegaconf.errors import OmegaConfBaseException

from omegakit.core.errors import ConfigLoadError
from omegakit.core.file import load_yaml
from omegakit.core.tree import select_node
from omegakit.core.utils import describe_error

IMPORT_KEY = "~import"
"""Value prefix that replaces a node with another config file or one of its nodes."""


def resolve_imports(
    config: DictConfig, file_path: Path, import_root: Path | None
) -> None:
    """Replace every `~import` value in `config` in place, depth-first.

    Args:
        config: The config loaded from `file_path`.
        file_path: The resolved path of the file; relative imports resolve against
            its directory.
        import_root: The resolved directory that every imported file must be in, or
            `None` for no restriction.

    Raises:
        ConfigLoadError: If an import is invalid, cannot be read, leaves
            `import_root`, or forms a cycle.
    """  # noqa: DOC502
    _resolve_imports(config, file_path, {file_path}, {}, import_root)


def _resolve_imports(
    config: DictConfig | ListConfig,
    config_path: Path,
    visited_paths: set[Path],
    cache: dict[Path, DictConfig | ListConfig],
    import_root: Path | None,
) -> None:
    # `visited_paths` holds the files of the current import chain, and `cache` the
    # files already loaded during this `load_config` call.
    if isinstance(config, ListConfig):
        for index in range(len(config)):
            node = config._get_node(index)
            if isinstance(node, (DictConfig, ListConfig)):
                _resolve_imports(node, config_path, visited_paths, cache, import_root)
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
            _resolve_imports(value, config_path, visited_paths, cache, import_root)
        elif isinstance(value, str) and value.startswith(IMPORT_KEY):
            config[key] = _load_import(
                config, key, value, config_path, visited_paths, cache, import_root
            )


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
            imported_config = load_yaml(file_path)
        except (OSError, ConfigLoadError) as error:
            raise ConfigLoadError(
                f"Cannot import `{statement}` in `{config_path}`: {error}"
            ) from error
        _resolve_imports(
            imported_config,
            file_path,
            {*visited_paths, file_path},
            cache,
            import_root,
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
