from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from omegaconf import DictConfig, ListConfig, OmegaConf

from .assembly import (
    exclude_keys_recursive,
    merge_base_recursive,
    resolve_defaults_recursive,
    resolve_imports,
)
from .keys import CLASS_KEY, META_KEY, PARTIAL_KEY, REF_KEY

type PathLike = Path | str


def load_config(
    file_path: PathLike,
    *,
    overrides: DictConfig | dict[str, Any] | list[str] | None = None,
    keep_targets: bool = True,
    keep_meta: bool = False,
) -> DictConfig:
    """Load a YAML configuration file from a given file path.

    Args:
        file_path: The path to the configuration file.
        overrides: Additional configuration overrides. Can be provided as a
            DictConfig, a regular dictionary, or a list of `key=value` strings (e.g.
            `["foo=1.0", "bar=baz"]`). Defaults to `None`.
        keep_targets: Whether to keep target fields needed for instantiation in the
            parsed config. Defaults to `True`.
        keep_meta: Whether to keep metadata fields in the parsed config. Defaults to
            `False`.

    Returns:
        The parsed configuration.
    """
    file_path = Path(file_path).resolve()
    config = cast(DictConfig, OmegaConf.load(file_path))
    resolve_imports(config, file_path, visited_paths={file_path}, cache={})
    merge_base_recursive(config)
    resolve_defaults_recursive(config)
    if overrides is not None:
        overrides = cast_overrides(overrides)
        config.merge_with(overrides)
    if keep_meta and keep_targets:
        return config
    exclude_keys = set()
    if not keep_meta:
        exclude_keys.add(META_KEY)
    if not keep_targets:
        exclude_keys.add(REF_KEY)
        exclude_keys.add(CLASS_KEY)
        exclude_keys.add(PARTIAL_KEY)
    exclude_keys_recursive(config, exclude_keys)
    return config


def cast_overrides(
    overrides: DictConfig | dict[str, Any] | list[str],
) -> DictConfig:
    """Convert overrides into a `DictConfig`.

    Args:
        overrides: A `DictConfig`, a dictionary, or a list of `key=value` strings.

    Returns:
        The overrides as a `DictConfig`.

    Raises:
        ValueError: If `overrides` has another type.
    """
    if isinstance(overrides, (DictConfig, ListConfig)):
        return cast(DictConfig, overrides)
    elif isinstance(overrides, dict):
        return OmegaConf.create(overrides)
    elif isinstance(overrides, list):
        return OmegaConf.from_dotlist(overrides)
    raise ValueError(
        f"Unsupported overrides type: {type(overrides)}. Expected `Config`, `dict` "
        "or `list` of `key=value` string pairs."
    )
