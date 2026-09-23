import pytest

from omegakit import instantiate
from tests.helpers import POINT

# Contracts: §5 Instantiation.


def test_instantiate_ref_imports_object():
    obj = instantiate({"$class": POINT, "x": {"$ref": "builtins.int"}, "y": 2})
    assert obj.x is int


def test_instantiate_ref_with_extra_keys_raises():
    with pytest.raises(ValueError, match="cannot contain any other keys"):
        instantiate(
            {"$class": POINT, "x": {"$ref": "builtins.int", "extra": 1}, "y": 2}
        )


def test_ref_allows_meta_sibling():
    obj = instantiate(
        {"$class": POINT, "x": {"$ref": "builtins.int", "$meta": 1}, "y": 2}
    )
    assert obj.x is int


def test_ref_in_list():
    obj = instantiate({"$class": POINT, "x": [{"$ref": "builtins.int"}], "y": 2})
    assert obj.x == [int]


def test_ref_at_top_level_is_not_instantiable():
    with pytest.raises(ValueError, match="Cannot instantiate config with no"):
        instantiate({"$ref": "builtins.int"})


def test_ref_unknown_attribute_raises():
    with pytest.raises(ImportError, match="Could not import"):
        instantiate({"$class": POINT, "x": {"$ref": "builtins.nope"}, "y": 2})
