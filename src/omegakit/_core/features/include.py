import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar

from omegaconf import DictConfig, ListConfig, Node, OmegaConf, TupleConfig
from omegaconf.errors import (
    InterpolationResolutionError,
    MissingMandatoryValue,
    OmegaConfBaseException,
)

from omegakit._core.errors import (
    ConfigIncludeError,
    IncludeRootError,
    OmegaKitBaseException,
)
from omegakit._core.utils.copy import copy_with_root
from omegakit._core.utils.describe import describe_error
from omegakit._core.utils.notes import add_note
from omegakit._core.utils.path import PathLike, resolve_path
from omegakit._core.utils.walk import walk
from omegakit._core.utils.yaml import load_yaml

INCLUDE_KEY = "~include"
"""The prefix of a value that is replaced by a config file or one of its nodes."""

_INCLUDE_PATTERN = re.compile(rf"{INCLUDE_KEY}(\s|$)")
_NOT_FOUND = object()

TConfig = TypeVar("TConfig", bound=DictConfig | ListConfig | TupleConfig)


@dataclass(frozen=True)
class _Assignment:
    parent: DictConfig | ListConfig
    key: Any
    value: Any


def resolve_includes(  # noqa: DOC502
    config: TConfig,
    config_path: PathLike,
    include_root: PathLike | None = None,
    copy: bool = True,
) -> TConfig:
    """Replace every `~include` value with the config node that it names.

    Args:
        config: The config to transform.
        config_path: The path of the file that `config` represents.
        include_root: The directory that every `~include` must stay under. Defaults to
            `None`, in which case any file may be included.
        copy: Whether to leave `config` unchanged. Defaults to `True`.

    Returns:
        The config with every `~include` resolved.

    Raises:
        ConfigFileNotFoundError: If an included file does not exist.
        ConfigFilePermissionError: If an included file may not be read.
        ConfigFileSyntaxError: If an included file is no valid YAML.
        ConfigIncludeError: If an `~include` cannot be resolved.
        IncludeRootError: If an included file is outside `include_root`.
    """
    if copy:
        config = copy_with_root(config)
    config_path = resolve_path(config_path)
    if include_root is not None:
        include_root = resolve_path(include_root)
    _resolve_includes(
        config, config_path, include_root, active_paths=[config_path], cache={}
    )
    return config


def _resolve_includes(
    config: DictConfig | ListConfig | TupleConfig,
    config_path: Path,
    include_root: Path | None,
    active_paths: list[Path],
    cache: dict[Path, DictConfig | ListConfig],
) -> None:
    # Assigned after the walk, so that no include sees the result of another
    included_values: list[_Assignment] = []
    for node in walk(config):
        value = node._value()
        if not isinstance(value, str) or not _INCLUDE_PATTERN.match(value):
            continue
        parent = node._get_parent()
        try:
            if not isinstance(parent, (DictConfig, ListConfig)):
                raise ConfigIncludeError("An item of a tuple cannot include.")
            included_value = _load_include(
                node, config_path, include_root, active_paths, cache
            )
        except OmegaKitBaseException as error:
            # The error carries the include that failed, and notes name the ones before
            if error.file_path is None:
                error.full_key = node._get_full_key(None)
                error.file_path = config_path
            else:
                add_note(
                    error,
                    f"  from `{value}` at `{node._get_full_key(None)}` in "
                    f"`{config_path}`",
                )
            raise
        included_values.append(_Assignment(parent, node._key(), included_value))
    for assignment in included_values:
        assignment.parent[assignment.key] = assignment.value


def _load_include(
    node: Node,
    current_path: Path,
    include_root: Path | None,
    active_paths: list[Path],
    cache: dict[Path, DictConfig | ListConfig],
) -> Any:
    try:
        # Resolves interpolations in the statement, as in `~include ${dir}/a.yaml`
        statement = node._dereference_node()._value()
    except InterpolationResolutionError as error:
        raise ConfigIncludeError(
            f"Cannot resolve the include: {describe_error(error)}"
        ) from error
    file_path, node_path = _parse_statement(statement)
    try:
        file_path = resolve_path(file_path, relative_to=current_path.parent)
    except (OSError, ValueError) as error:
        raise ConfigIncludeError(f"`{file_path}` is not a valid path.") from error
    if include_root is not None and not file_path.is_relative_to(include_root):
        raise IncludeRootError(
            f"`{file_path}` is outside the include root `{include_root}`."
        )
    if file_path in active_paths:
        cycle_paths = [*active_paths[active_paths.index(file_path) :], file_path]
        cycle = " -> ".join(f"`{path}`" for path in cycle_paths)
        raise ConfigIncludeError(f"The includes form a cycle: {cycle}.")
    if file_path not in cache:
        loaded_config = load_yaml(file_path)
        _resolve_includes(
            loaded_config, file_path, include_root, [*active_paths, file_path], cache
        )
        cache[file_path] = loaded_config
    try:
        selected_value = OmegaConf.select(
            cache[file_path], node_path, default=_NOT_FOUND, throw_on_missing=True
        )
    except MissingMandatoryValue as error:
        raise ConfigIncludeError(
            f"`{node_path}` in `{file_path}` holds `???`."
        ) from error
    except InterpolationResolutionError as error:
        raise ConfigIncludeError(
            f"Cannot resolve `{node_path}` in `{file_path}`: {describe_error(error)}"
        ) from error
    except OmegaConfBaseException as error:
        raise ConfigIncludeError(f"`{file_path}` has no node `{node_path}`.") from error
    if selected_value is _NOT_FOUND:
        raise ConfigIncludeError(f"`{file_path}` has no node `{node_path}`.")
    if isinstance(selected_value, str):
        # A resolved string must not be read as an interpolation again
        selected_value = re.sub(r"(\\*)\$\{", r"\1\1\\${", selected_value)
    return selected_value


def _parse_statement(statement: str) -> tuple[Path, str]:
    include_arg = statement[len(INCLUDE_KEY) :]
    file_path, _, node_path = include_arg.partition("#")
    file_path = file_path.strip()
    node_path = node_path.strip()
    if not file_path:
        raise ConfigIncludeError("The include names no file.")
    if "#" in node_path:
        raise ConfigIncludeError("The include contains more than one `#`.")
    return Path(file_path), node_path
