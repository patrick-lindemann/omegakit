from omegakit import instantiate
from tests.helpers import DOUBLED_POINT, ConfigurablePoint, DoubledPoint

# Contracts: §5 Instantiation.


def test_from_config_builds_from_mapping():
    point = ConfigurablePoint.from_config({"x": 1, "y": 2})
    assert (point.x, point.y) == (1, 2)


def test_from_config_returns_instance():
    assert isinstance(
        ConfigurablePoint.from_config({"x": 0, "y": 0}), ConfigurablePoint
    )


def test_instantiate_uses_custom_from_config():
    obj = instantiate({"$class": DOUBLED_POINT, "x": 1, "y": 2})
    assert isinstance(obj, DoubledPoint)
    assert (obj.x, obj.y) == (2, 2)
