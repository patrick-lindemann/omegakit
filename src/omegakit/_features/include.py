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
from omegakit._core.copy import copy_with_root
from omegakit._core.error import OmegaKitBaseException
from omegakit._core.file import load_yaml
from omegakit._core.walk import walk
from omegakit._utils.describe import describe_error
from omegakit._utils.path import PathLike, resolve_path

INCLUDE_PREFIX = "~include"

_INCLUDE_PATTERN = re.compile(rf"{INCLUDE_PREFIX}(\s|$)")
_NOT_FOUND = object()


class ConfigIncludeError(OmegaKitBaseException):
    pass


class IncludeSyntaxError(ConfigIncludeError, ValueError):
    pass


class IncludeInterpolationError(ConfigIncludeError, InterpolationResolutionError):
    pass


class IncludeTypeError(ConfigIncludeError, TypeError):
    pass


class IncludeCycleError(ConfigIncludeError):
    pass


class IncludeNodeNotFoundError(ConfigIncludeError):
    pass


class IncludeMissingValueError(ConfigIncludeError, MissingMandatoryValue):
    pass


def resolve_includes[TConfig: DictConfig | ListConfig | TupleConfig](
    config: TConfig, config_path: PathLike, copy: bool = True
) -> TConfig:
    if copy:
        config = copy_with_root(config)
    config_path = resolve_path(config_path)
    _resolve_includes(config, config_path, active_paths={config_path}, cache={})
    return config


def _resolve_includes(
    config: DictConfig | ListConfig | TupleConfig,
    config_path: Path,
    active_paths: set[Path],
    cache: dict[Path, DictConfig | ListConfig],
) -> None:
    # Assigned after the walk, so that no include sees the result of another
    included_values: list[Assignment] = []
    for node in walk(config):
        value = node._value()
        if not isinstance(value, str) or not _INCLUDE_PATTERN.match(value):
            continue
        parent = node._get_parent()
        try:
            if not isinstance(parent, (DictConfig, ListConfig)):
                raise IncludeTypeError("An item of a tuple cannot include.")
            included_value = _load_include(node, config_path, active_paths, cache)
        except OmegaKitBaseException as error:
            error.add_note(
                f"  from `{value}` at `{node._get_full_key(None)}` in `{config_path}`"
            )
            raise
        included_values.append(Assignment(parent, node._key(), included_value))
    for assignment in included_values:
        assignment.parent[assignment.key] = assignment.value


def _load_include(
    node: Node,
    current_path: Path,
    active_paths: set[Path],
    cache: dict[Path, DictConfig | ListConfig],
) -> Any:
    try:
        # Resolves interpolations in the statement, as in `~include ${dir}/a.yaml`
        statement = node._dereference_node()._value()
    except InterpolationResolutionError as error:
        raise IncludeInterpolationError(
            f"Cannot resolve the include: {describe_error(error)}"
        ) from error
    file_path, node_path = _parse_statement(statement)
    try:
        file_path = resolve_path(file_path, relative_to=current_path.parent)
    except (OSError, ValueError) as error:
        raise IncludeSyntaxError(f"`{file_path}` is not a valid path.") from error
    if file_path in active_paths:
        raise IncludeCycleError(f"`{file_path}` is already being loaded.")
    if file_path not in cache:
        loaded_config = load_yaml(file_path)
        _resolve_includes(loaded_config, file_path, {*active_paths, file_path}, cache)
        cache[file_path] = loaded_config
    try:
        selected_value = OmegaConf.select(
            cache[file_path], node_path, default=_NOT_FOUND, throw_on_missing=True
        )
    except MissingMandatoryValue as error:
        raise IncludeMissingValueError(
            f"`{node_path}` in `{file_path}` holds `???`."
        ) from error
    except InterpolationResolutionError as error:
        raise IncludeInterpolationError(
            f"Cannot resolve `{node_path}` in `{file_path}`: {describe_error(error)}"
        ) from error
    except OmegaConfBaseException as error:
        raise IncludeNodeNotFoundError(
            f"`{file_path}` has no node `{node_path}`."
        ) from error
    if selected_value is _NOT_FOUND:
        raise IncludeNodeNotFoundError(f"`{file_path}` has no node `{node_path}`.")
    if isinstance(selected_value, str):
        # A resolved string must not be read as an interpolation again
        selected_value = selected_value.replace("${", "\\${")
    return selected_value


def _parse_statement(statement: str) -> tuple[Path, str]:
    include_arg = statement[len(INCLUDE_PREFIX) :]
    file_path, _, node_path = include_arg.partition("#")
    file_path = file_path.strip()
    node_path = node_path.strip()
    if not file_path:
        raise IncludeSyntaxError("The include names no file.")
    if "#" in node_path:
        raise IncludeSyntaxError("The include contains more than one `#`.")
    return Path(file_path), node_path
