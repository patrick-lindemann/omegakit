import pytest

from omegakit import instantiate, make_node
from tests import schemas

# Contracts: §10 Typed configs (make_node).


class Holder:
    class Inner:
        """A nested class, which cannot be imported by its path."""


def test_node_creates_class_node():
    assert make_node(schemas.Encoder, width=2) == {
        "$class": "tests.schemas.Encoder",
        "width": 2,
    }


def test_node_is_instantiable():
    assert (
        instantiate(make_node(schemas.make_encoder, width=3), schemas.Encoder).width
        == 3
    )


def test_node_child_is_validated_against_its_schema():
    assert instantiate(make_node(schemas.TypedEncoder, width="3")).width == 3


def test_node_rejects_nested_classes():
    with pytest.raises(ValueError, match="module level"):
        make_node(Holder.Inner)


def test_node_rejects_local_objects():
    local = type("Local", (), {"__qualname__": "factory.<locals>.Local"})
    with pytest.raises(ValueError, match="module level"):
        make_node(local)
