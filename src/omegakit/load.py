from typing import Any

from omegaconf import DictConfig

from ._core.error import OmegaKitBaseException
from ._core.utils.file import load_yaml
from ._core.utils.path import PathLike, resolve_path
from ._features.base import merge_bases
from ._features.each import apply_each
from ._features.include import resolve_includes
from ._features.meta import remove_meta
from ._features.overrides import apply_overrides


class ConfigLoadError(OmegaKitBaseException):
    pass


class LoadTypeError(ConfigLoadError, TypeError):
    pass


def load_config(
    file_path: PathLike,
    overrides: DictConfig | dict[str, Any] | list[str] | None = None,
    keep_meta: bool = False,
    include_root: PathLike | None = None,
) -> DictConfig:
    """Load a YAML config file and assemble it.

    Args:
        file_path: The config file.
        overrides: Values merged on top of the assembled config: a `DictConfig`, a
            `dict`, or a list of `key=value` strings. Defaults to `None`.
        keep_meta: Keep `$meta`. Defaults to `False`.
        include_root: A directory that every `~include` must stay in. Defaults to
            `None`, which allows any file.

    Returns:
        The assembled config.

    Raises:
        LoadTypeError: If the root of the file is a list.
    """
    file_path = resolve_path(file_path)
    config = load_yaml(file_path)
    if not isinstance(config, DictConfig):
        raise LoadTypeError(
            f"Cannot load `{file_path}`: its root is a list, but the root of a config "
            "must be a mapping."
        )
    # The config is this function's own, so no step needs to copy it
    config = resolve_includes(config, file_path, include_root, copy=False)
    config = merge_bases(config, copy=False)
    config = apply_each(config, copy=False)
    if overrides is not None:
        config = apply_overrides(config, overrides, copy=False)
    if not keep_meta:
        config = remove_meta(config, copy=False)
    return config
