from pathlib import Path

type PathLike = Path | str


def cast_path(path: PathLike) -> Path:
    return path if isinstance(path, Path) else Path(path)


def resolve_path(path: PathLike, relative_to: PathLike | None = None) -> Path:
    path = cast_path(path)
    if path.is_absolute() or relative_to is None:
        return path.resolve()
    relative_to = cast_path(relative_to)
    return Path(relative_to, path).resolve()
