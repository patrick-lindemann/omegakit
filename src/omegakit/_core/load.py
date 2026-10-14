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


def load_config(
    file_path: PathLike,
    overrides: DictConfig | dict[str, Any] | list[str] | None = None,
    keep_meta: bool = False,
    include_root: PathLike | None = None,
) -> DictConfig:
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
