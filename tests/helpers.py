from omegakit import Configurable

POINT = "tests.helpers.Point"
CONFIGURABLE_POINT = "tests.helpers.ConfigurablePoint"
CONTAINER = "tests.helpers.Container"


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
