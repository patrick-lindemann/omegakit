from pathlib import Path
from typing import Any

import yaml
from omegaconf import DictConfig, OmegaConf
from omegaconf.errors import OmegaConfBaseException

from .assembly import (
    apply_defaults,
    load_file,
    merge_bases,
    resolve_imports,
    strip_keys,
)
from .errors import ConfigLoadError, OmegaKitBaseException
from .keys import CLASS_KEY, META_KEY, PARTIAL_KEY, REF_KEY
from .utils import describe_error


def load_config(
    file_path: Path | str,
    *,
    overrides: DictConfig | dict[str, Any] | list[str] | None = None,
    keep_targets: bool = True,
    keep_meta: bool = False,
    import_root: Path | str | None = None,
) -> DictConfig:
    """Load a YAML config file and assemble it.

    The file is read, then every `~import` is replaced, recursively, then every
    `$base` is merged underneath its node and every `$defaults` under its siblings,
    and finally the overrides are merged on top. Interpolations stay unresolved,
    except in `~import` paths and in `$base` and `$defaults` values, which need them
    while assembling.

    Args:
        file_path: The config file.
        overrides: Values merged on top of the assembled config: a `DictConfig`, a
            `dict`, or a list of `key=value` strings such as `["model.depth=4"]`.
            Defaults to `None`.
        keep_targets: Keep `$class`, `$ref` and `$partial`. Without them, the
            config is plain data. Defaults to `True`.
        keep_meta: Keep `$meta`. Defaults to `False`.
        import_root: A directory that every `~import` must stay in, after
            interpolations and symbolic links are resolved. An import outside it
            raises `ConfigLoadError`, and a directory that does not exist raises
            `FileNotFoundError`. Defaults to `None`, which allows any file.

    Returns:
        The parsed configuration.

    Raises:
        ConfigLoadError: If a file, an import, a `$base` or `$defaults` value, or
            an override is invalid. A missing root file raises
            `FileNotFoundError`.
        NotADirectoryError: If `import_root` is not a directory.
    """  # noqa: DOC503
    if import_root is not None:
        import_root = Path(import_root).resolve(strict=True)
        if not import_root.is_dir():
            raise NotADirectoryError(f"`{import_root}` is not a directory.")
    file_path = Path(file_path).resolve()
    config = load_file(file_path)
    if not isinstance(config, DictConfig):
        raise ConfigLoadError(
            f"Cannot load `{file_path}`: its root is a list, but the root of a config "
            "must be a mapping."
        )
    try:
        resolve_imports(
            config,
            file_path,
            visited_paths={file_path},
            cache={},
            import_root=import_root,
        )
        merge_bases(config)
        apply_defaults(config)
    except OmegaKitBaseException:
        raise
    except OmegaConfBaseException as error:
        raise ConfigLoadError(
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
        ConfigLoadError: If an override does not parse, has a value of an
            unsupported type, or is rejected by `config`.
    """  # noqa: DOC503
    try:
        config.merge_with(_parse_overrides(overrides))
    except OmegaKitBaseException:
        raise
    except OmegaConfBaseException as error:
        location = f" `{error.full_key}`" if error.full_key else ""
        raise ConfigLoadError(
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
                raise ConfigLoadError(
                    f"Cannot parse the override `{override}`: {describe_error(error)}"
                ) from error
        return parsed
    raise TypeError(
        f"Unsupported overrides type: {type(overrides)}. Expected a `DictConfig`, a "
        "`dict` or a `list` of `key=value` strings."
    )
