from typing import Any, override

from omegakit import Configurable

POINT = "tests.helpers.Point"
CONFIGURABLE_POINT = "tests.helpers.ConfigurablePoint"
CONTAINER = "tests.helpers.Container"
DOUBLED_POINT = "tests.helpers.DoubledPoint"
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


class DoubledPoint(ConfigurablePoint):
    """A `Configurable` point with a custom `from_config` that doubles `x`."""

    @classmethod
    @override
    def from_config(cls, config: Any, **kwargs: Any) -> "DoubledPoint":
        return cls(x=config["x"] * 2, y=config["y"])


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
