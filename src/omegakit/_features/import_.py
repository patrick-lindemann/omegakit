import re
from pathlib import Path
from typing import Any

from omegaconf import DictConfig, ListConfig, Node, OmegaConf, TupleConfig
from omegaconf.errors import (
    InterpolationResolutionError,
    MissingMandatoryValue,
    OmegaConfBaseException,
)

from omegakit._core.assignment import Assignment
from omegakit._core.error import OmegaKitBaseException
from omegakit._core.file import load_yaml
from omegakit._core.merge import copy_with_root
from omegakit._core.walk import walk
from omegakit._utils.describe import describe_error
from omegakit._utils.path import PathLike, resolve_path

IMPORT_KEY = "~import"

_IMPORT_PATTERN = re.compile(rf"{IMPORT_KEY}(\s|$)")
_NOT_FOUND = object()


class ConfigImportError(OmegaKitBaseException):
    pass


class ImportSyntaxError(ConfigImportError, ValueError):
    pass


class ImportInterpolationError(ConfigImportError, InterpolationResolutionError):
    pass


class ImportTypeError(ConfigImportError, TypeError):
    pass


class ImportCycleError(ConfigImportError):
    pass


class ImportNodeNotFoundError(ConfigImportError):
    pass


class ImportMissingValueError(ConfigImportError, MissingMandatoryValue):
    pass


def resolve_imports[ConfigT: DictConfig | ListConfig | TupleConfig](
    config: ConfigT, config_path: PathLike, copy: bool = True
) -> ConfigT:
    if copy:
        config = copy_with_root(config)
    config_path = resolve_path(config_path)
    _resolve_imports(config, config_path, active_paths={config_path}, cache={})
    return config


def _resolve_imports(
    config: DictConfig | ListConfig | TupleConfig,
    config_path: Path,
    active_paths: set[Path],
    cache: dict[Path, DictConfig | ListConfig],
) -> None:
    # Assigned after the walk, so that no import sees the result of another
    imported_values: list[Assignment] = []
    for node in walk(config):
        value = node._value()
        if not isinstance(value, str) or not _IMPORT_PATTERN.match(value):
            continue
        parent = node._get_parent()
        try:
            if not isinstance(parent, (DictConfig, ListConfig)):
                raise ImportTypeError("An item of a tuple cannot import.")
            imported_value = _load_import(node, config_path, active_paths, cache)
        except OmegaKitBaseException as error:
            error.add_note(
                f"  from `{value}` at `{node._get_full_key(None)}` in `{config_path}`"
            )
            raise
        imported_values.append(Assignment(parent, node._key(), imported_value))
    for assignment in imported_values:
        assignment.parent[assignment.key] = assignment.value


def _load_import(
    node: Node,
    current_path: Path,
    active_paths: set[Path],
    cache: dict[Path, DictConfig | ListConfig],
) -> Any:
    try:
        # Resolves interpolations in the statement, as in `~import ${dir}/a.yaml`
        statement = node._dereference_node()._value()
    except InterpolationResolutionError as error:
        raise ImportInterpolationError(
            f"Cannot resolve the import: {describe_error(error)}"
        ) from error
    file_path, node_path = _parse_statement(statement)
    try:
        file_path = resolve_path(file_path, relative_to=current_path.parent)
    except (OSError, ValueError) as error:
        raise ImportSyntaxError(f"`{file_path}` is not a valid path.") from error
    if file_path in active_paths:
        raise ImportCycleError(f"`{file_path}` is already being loaded.")
    if file_path not in cache:
        loaded_config = load_yaml(file_path)
        _resolve_imports(loaded_config, file_path, {*active_paths, file_path}, cache)
        cache[file_path] = loaded_config
    try:
        selected_value = OmegaConf.select(
            cache[file_path], node_path, default=_NOT_FOUND, throw_on_missing=True
        )
    except MissingMandatoryValue as error:
        raise ImportMissingValueError(
            f"`{node_path}` in `{file_path}` holds `???`."
        ) from error
    except InterpolationResolutionError as error:
        raise ImportInterpolationError(
            f"Cannot resolve `{node_path}` in `{file_path}`: {describe_error(error)}"
        ) from error
    except OmegaConfBaseException as error:
        raise ImportNodeNotFoundError(
            f"`{file_path}` has no node `{node_path}`."
        ) from error
    if selected_value is _NOT_FOUND:
        raise ImportNodeNotFoundError(f"`{file_path}` has no node `{node_path}`.")
    if isinstance(selected_value, str):
        # A resolved string must not be read as an interpolation again
        selected_value = selected_value.replace("${", "\\${")
    return selected_value


def _parse_statement(statement: str) -> tuple[Path, str]:
    import_arg = statement[len(IMPORT_KEY) :]
    file_path, _, node_path = import_arg.partition("#")
    file_path = file_path.strip()
    node_path = node_path.strip()
    if not file_path:
        raise ImportSyntaxError("The import names no file.")
    if "#" in node_path:
        raise ImportSyntaxError("The import contains more than one `#`.")
    return Path(file_path), node_path
