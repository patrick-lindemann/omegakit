from typing import Any

from omegaconf import DictConfig

from .errors import ConfigFileSyntaxError
from .features import (
    apply_each,
    apply_overrides,
    merge_bases,
    remove_meta,
    resolve_includes,
)
from .utils.path import PathLike, resolve_path
from .utils.yaml import load_yaml


def load_config(  # noqa: DOC503
    file_path: PathLike,
    overrides: DictConfig | dict[str, Any] | list[str] | None = None,
    keep_meta: bool = False,
    include_root: PathLike | None = None,
) -> DictConfig:
    """Load a config file and assemble it.

    The includes are resolved first. Then `$base` and `$each` are merged, the
    overrides are applied and `$meta` is removed.

    Args:
        file_path: The YAML config file.
        overrides: A mapping, or a list of `key=value` strings applied in order.
            Defaults to `None`.
        keep_meta: Whether to keep the `$meta` keys. Defaults to `False`.
        include_root: The directory that every `~include` must stay under. Defaults to
            `None`, in which case any file may be included.

    Returns:
        The assembled config.

    Raises:
        ConfigFileNotFoundError: If `file_path` or an included file does not exist.
        ConfigFilePermissionError: If a config file may not be read.
        ConfigFileSyntaxError: If a config file is no valid YAML, or the root of
            `file_path` is no mapping.
        ConfigIncludeError: If an `~include` cannot be resolved, or names a file
            outside `include_root`.
        ConfigMergeError: If a `$base` or `$each` cannot be merged.
        ConfigOverrideError: If an override cannot be parsed or applied.
    """
    file_path = resolve_path(file_path)
    config = load_yaml(file_path)
    if not isinstance(config, DictConfig):
        raise ConfigFileSyntaxError(
            f"Cannot load `{file_path}`: its root is a list, but the root of a config "
            "must be a mapping."
        )
    config = resolve_includes(config, file_path, include_root, copy=False)
    config = merge_bases(config, copy=False)
    config = apply_each(config, copy=False)
    if overrides is not None:
        config = apply_overrides(config, overrides, copy=False)
    if not keep_meta:
        config = remove_meta(config, copy=False)
    return config
