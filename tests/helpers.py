from typing import Any

from omegakit import Configurable

POINT = "tests.helpers.Point"
CONFIGURABLE_POINT = "tests.helpers.ConfigurablePoint"
CONTAINER = "tests.helpers.Container"
FAILING = "tests.helpers.Failing"
RECORDER = "tests.helpers.Recorder"


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


class Recorder:
    """Returns the arguments its duck-typed `from_config` receives."""

    @classmethod
    def from_config(
        cls, config: dict[str, Any], **kwargs: Any
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        return config, kwargs


class Failing:
    """Raises an exception whose constructor takes several arguments."""

    def __init__(self) -> None:
        raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")
