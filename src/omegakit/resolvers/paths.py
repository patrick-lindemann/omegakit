from collections.abc import Mapping
from pathlib import Path

from omegaconf import OmegaConf


def register_paths_resolver(
    paths: Mapping[str, str | Path], *, replace: bool = False, use_cache: bool = True
) -> None:
    """__summary__"""
    values = {key: str(value) for key, value in paths.items()}
    OmegaConf.register_resolver(
        "paths", values.get, replace=replace, use_cache=use_cache
    )
