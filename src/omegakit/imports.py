import importlib
from pathlib import Path
from typing import Any

import yaml
from omegaconf import DictConfig, ListConfig, Node, OmegaConf
from omegaconf.errors import OmegaConfBaseException

from .errors import ConfigLoadError, OmegaKitBaseException, describe_error
from .keys import IMPORT_KEY
from .walk import select_node

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


def import_object(import_path: str) -> Any:
    """Import an object by its dotted path, such as `package.module.Name`.

    Args:
        import_path: The module path and attribute name, separated by a dot.

    Returns:
        The imported object.

    Raises:
        ImportError: If `import_path` is not a dotted path of at least two names, if
            the module cannot be imported, or if it has no attribute of that name.
            The first and the last carry `import_path` as their `name`.
    """
    if not all(import_path.split(".")) or "." not in import_path:
        raise ImportError(
            f"`{import_path}` is not an import path of the form `package.module.Name`.",
            name=import_path,
        )
    module_path, _, attr_name = import_path.rpartition(".")
    module = importlib.import_module(module_path)
    try:
        return getattr(module, attr_name)
    except AttributeError as error:
        raise ImportError(
            f"Module `{module_path}` has no attribute `{attr_name}`.",
            name=import_path,
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
