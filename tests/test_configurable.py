from tests.helpers import ConfigurablePoint


def test_from_config_builds_from_mapping():
    point = ConfigurablePoint.from_config({"x": 1, "y": 2})
    assert (point.x, point.y) == (1, 2)


def test_from_config_returns_instance():
    assert isinstance(
        ConfigurablePoint.from_config({"x": 0, "y": 0}), ConfigurablePoint
    )
