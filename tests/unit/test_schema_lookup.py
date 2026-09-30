from typing import Any

import pytest

from omegakit import Configurable, SchemaDefinitionError, instantiate, validate
from tests.schemas import TypedEncoder


class Inherited(TypedEncoder):
    """Inherits the schema of its base."""


class WithoutSchema(TypedEncoder):
    """Sets the schema of its base back to `None`."""

    schema = None

    def __init__(self, **fields: Any) -> None:
        self.fields = fields


class NotADataclass(Configurable):
    """Names a schema that is not a dataclass."""

    schema = dict  # pyright: ignore[reportAssignmentType]


def test_lookup_schema_attribute():
    obj = instantiate({"$class": "tests.schemas.TypedEncoder", "width": "3"})
    assert obj.width == 3


def test_lookup_inherited_schema():
    assert instantiate({"$class": f"{__name__}.Inherited", "width": "3"}).width == 3


def test_lookup_schema_set_to_none_has_no_schema():
    obj = instantiate({"$class": f"{__name__}.WithoutSchema", "width": "3"})
    assert obj.fields == {"width": "3"}


def test_lookup_bare_configurable_has_no_schema():
    obj = instantiate({"$class": "tests.schemas.Untyped", "anything": "3"})
    assert obj.fields == {"anything": "3"}


def test_lookup_schema_that_is_not_a_dataclass_raises():
    with pytest.raises(SchemaDefinitionError, match="is not a dataclass"):
        validate({}, schema=NotADataclass)
