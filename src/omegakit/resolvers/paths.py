from collections.abc import Mapping
from pathlib import Path

from ._register import register_resolver


def register_paths_resolver(
    paths: Mapping[str, str | Path], *, replace: bool = False
) -> None:
    """Register `${paths:key}`, which gives the path registered under `key`.

    Args:
        paths: The paths by key.
        replace: Replace a resolver named `paths`. Defaults to `False`.

    Raises:
        ValueError: If a resolver named `paths` exists and `replace` is `False`.
    """  # noqa: DOC502
    values = {key: str(value) for key, value in paths.items()}
    register_resolver("paths", values.get, replace=replace)
