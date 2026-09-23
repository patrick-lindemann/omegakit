import pytest

from omegakit import instantiate
from tests.helpers import (
    POINT,
)


def test_instantiate_ref_imports_object():
    obj = instantiate({"$class": POINT, "x": {"$ref": "builtins.int"}, "y": 2})
    assert obj.x is int


def test_instantiate_ref_with_extra_keys_raises():
    with pytest.raises(ValueError, match="cannot contain any other keys"):
        instantiate(
            {"$class": POINT, "x": {"$ref": "builtins.int", "extra": 1}, "y": 2}
        )
