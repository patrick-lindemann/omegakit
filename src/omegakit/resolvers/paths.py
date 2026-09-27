from collections.abc import Mapping
from pathlib import Path

from omegakit._utils import register_resolver


def register_paths_resolver(
    paths: Mapping[str, str | Path], *, replace: bool = False
) -> None:
    """Register `${paths:key}`, which gives the path registered under `key`.

    The paths are copied and converted to strings, without being resolved. An
    unknown key gives `None`. Registration is global to OmegaConf.

    Args:
        paths: The paths by key.
        replace: Replace a resolver named `paths`. Defaults to `False`.
    """
    values = {key: str(value) for key, value in paths.items()}
    register_resolver("paths", values.get, replace=replace)
