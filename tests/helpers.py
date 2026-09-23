from pathlib import Path
from textwrap import dedent

from config_compose import Configurable


class Point:
    """A plain (non-`Configurable`) class built via `$class` in config tests."""

    def __init__(self, x: int, y: int) -> None:
        self.x = x
        self.y = y


class ConfigurablePoint(Configurable):
    """A `Configurable` point whose `from_config` builds it from a mapping."""

    def __init__(self, x: int, y: int) -> None:
        self.x = x
        self.y = y


class Container:
    """Holds a nested object to exercise recursive instantiation."""

    def __init__(self, name: str, point: Point) -> None:
        self.name = name
        self.point = point


def write_text(path: Path, text: str) -> Path:
    path.write_text(dedent(text))
    return path
