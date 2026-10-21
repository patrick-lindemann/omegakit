from collections.abc import Mapping
from pathlib import Path

from omegaconf import OmegaConf


def register_paths_resolver(
    paths: Mapping[str, str | Path], *, replace: bool = False, use_cache: bool = True
) -> None:
    """Register `${paths:name}`, which resolves to the path of `name` as a `str`.

    Args:
        paths: The paths by name.
        replace: Whether to replace a registered resolver of the same name. Defaults
            to `False`.
        use_cache: Whether to cache each result by its arguments. Defaults to `True`.
    """
    values = {key: str(value) for key, value in paths.items()}

    # OmegaConf cannot read the signature of `dict.__getitem__` before Python 3.12
    def resolve(name: str) -> str:
        return values[name]

    OmegaConf.register_resolver("paths", resolve, replace=replace, use_cache=use_cache)
