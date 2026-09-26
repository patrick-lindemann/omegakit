from collections.abc import Mapping
from pathlib import Path

from omegakit._utils import register_resolver


def register_paths_resolver(
    paths: Mapping[str, str | Path], *, replace: bool = False
) -> None:
    """Register `${paths:key}` using a snapshot of caller-provided paths.

    Values are converted to strings without resolving them. Unknown keys return None,
    matching the original resolver. Registration is global to OmegaConf.
    """
    values = {key: str(value) for key, value in paths.items()}
    register_resolver("paths", values.get, replace=replace)
