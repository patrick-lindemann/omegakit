from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from omegaconf import DictConfig, OmegaConf
from omegaconf.errors import OmegaConfBaseException

from ._assembly import (
    apply_defaults,
    load_file,
    merge_bases,
    resolve_imports,
    strip_keys,
)
from ._keys import CLASS_KEY, META_KEY, PARTIAL_KEY, REF_KEY
from ._schema import ConfigValidationError
from ._utils import describe_error

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

    Raises:
        ConfigValidationError: If a file, an import or a `$base` or `$defaults`
            value is invalid. A missing root file raises `FileNotFoundError`.
    """
    file_path = Path(file_path).resolve()
    config = load_file(file_path)
    if not isinstance(config, DictConfig):
        raise ConfigValidationError(
            f"Cannot load `{file_path}`: its root is a list, but the root of a config "
            "must be a mapping."
        )
    try:
        resolve_imports(config, file_path, visited_paths={file_path}, cache={})
        merge_bases(config)
        apply_defaults(config)
    except OmegaConfBaseException as error:
        raise ConfigValidationError(
            f"Cannot load `{file_path}`: {str(error).splitlines()[0]}"
        ) from error
    if overrides is not None:
        merge_overrides(config, overrides)
    if keep_meta and keep_targets:
        return config
    exclude_keys = set()
    if not keep_meta:
        exclude_keys.add(META_KEY)
    if not keep_targets:
        exclude_keys.add(REF_KEY)
        exclude_keys.add(CLASS_KEY)
        exclude_keys.add(PARTIAL_KEY)
    strip_keys(config, exclude_keys)
    return config


def merge_overrides(
    config: DictConfig, overrides: DictConfig | dict[str, Any] | list[str]
) -> None:
    """Merge overrides into a config in place.

    Args:
        config: The config to change.
        overrides: A `DictConfig`, a dictionary, or a list of `key=value` strings.

    Raises:
        ConfigValidationError: If an override does not parse, has a value of an
            unsupported type, or is rejected by `config`.
    """
    try:
        config.merge_with(_parse_overrides(overrides))
    except OmegaConfBaseException as error:
        location = f" `{error.full_key}`" if error.full_key else ""
        raise ConfigValidationError(
            f"Cannot apply the override{location}: {describe_error(error)}"
        ) from error


def _parse_overrides(
    overrides: DictConfig | dict[str, Any] | list[str],
) -> DictConfig:
    if isinstance(overrides, DictConfig):
        return overrides
    elif isinstance(overrides, dict):
        return OmegaConf.create(overrides)
    elif isinstance(overrides, list):
        parsed = OmegaConf.create()
        for override in overrides:
            try:
                parsed.merge_with_dotlist([override])
            except (yaml.YAMLError, OmegaConfBaseException) as error:
                raise ConfigValidationError(
                    f"Cannot parse the override `{override}`: {describe_error(error)}"
                ) from error
        return parsed
    raise TypeError(
        f"Unsupported overrides type: {type(overrides)}. Expected a `DictConfig`, a "
        "`dict` or a `list` of `key=value` strings."
    )
