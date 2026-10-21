from pathlib import Path

from typing_extensions import TypeAliasType

PathLike = TypeAliasType("PathLike", Path | str)


def cast_path(path: PathLike) -> Path:
    """Make a `Path` of a `str`.

    Args:
        path: The path.

    Returns:
        `path` itself if it is a `Path`, else a new `Path`.
    """
    return path if isinstance(path, Path) else Path(path)


def resolve_path(path: PathLike, relative_to: PathLike | None = None) -> Path:
    """Make a path absolute.

    Args:
        path: The path.
        relative_to: The directory that a relative `path` starts at. Defaults to
            `None`, in which case it starts at the working directory.

    Returns:
        The absolute path, with symbolic links resolved.
    """
    path = cast_path(path)
    if path.is_absolute() or relative_to is None:
        return path.resolve()
    relative_to = cast_path(relative_to)
    return Path(relative_to, path).resolve()
