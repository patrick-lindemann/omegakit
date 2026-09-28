from pathlib import Path
from typing import Any

from omegaconf import DictConfig, ListConfig
from omegaconf.errors import OmegaConfBaseException

from .errors import ConfigLoadError, OmegaKitBaseException, describe_error
from .imports import load_file, resolve_imports
from .keys import CLASS_KEY, META_KEY, PARTIAL_KEY, REF_KEY
from .merge import apply_defaults, merge_bases
from .overrides import merge_overrides
from .walk import walk


def load_config(
    file_path: Path | str,
    *,
    overrides: DictConfig | dict[str, Any] | list[str] | None = None,
    keep_targets: bool = True,
    keep_meta: bool = False,
    import_root: Path | str | None = None,
) -> DictConfig:
    """Load a YAML config file and assemble it.

    Args:
        file_path: The config file.
        overrides: Values merged on top of the assembled config: a `DictConfig`, a
            `dict`, or a list of `key=value` strings such as `["model.depth=4"]`.
            Defaults to `None`.
        keep_targets: Keep `$class`, `$ref` and `$partial`. Defaults to `True`.
        keep_meta: Keep `$meta`. Defaults to `False`.
        import_root: A directory that every `~import` must stay in. Defaults to
            `None`, which allows any file.

    Returns:
        The assembled config.

    Raises:
        ConfigLoadError: If a file, an import, a `$base` or `$defaults` value, or
            an override is invalid.
        FileNotFoundError: If `file_path` or `import_root` does not exist.
        NotADirectoryError: If `import_root` is not a directory.
        TypeError: If `overrides` is not a `DictConfig`, a `dict` or a `list` of
            strings.
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
            f"Cannot load `{file_path}`: {describe_error(error)}"
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
    _strip_keys(config, exclude_keys)
    return config


def _strip_keys(config: DictConfig | ListConfig, exclude: set[str]) -> None:
    for node in walk(config):
        for key in list(node.keys()):
            if key in exclude:
                node.pop(key)
