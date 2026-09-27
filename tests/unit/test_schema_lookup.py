from typing import Any

import pytest
from typing_extensions import TypeVar

from omegakit import Configurable, SchemaDefinitionError, check_schema, instantiate
from tests.schemas import EncoderConfig, TypedEncoder

ConfigT = TypeVar("ConfigT")


class Mid(Configurable[ConfigT]):
    """A generic intermediate class without a type variable default."""

    def __init__(self, **fields: Any) -> None:
        self.fields = fields


DefaultT = TypeVar("DefaultT", default=EncoderConfig)


class MidWithDefault(Configurable[DefaultT]):
    """A generic intermediate class whose type variable defaults to a schema."""

    def __init__(self, **fields: Any) -> None:
        self.fields = fields


class Leaf(Mid[EncoderConfig]):
    """Parametrizes a generic intermediate class."""


class Mixin[T]:
    """A generic mixin that is not a `Configurable`."""


class MixedIn(Mixin[int], TypedEncoder):
    """Lists a generic mixin before its `Configurable` base."""


Unbound = TypeVar("Unbound")


class Broken(Configurable):
    """Claims a type variable in its bases that nothing can substitute."""


Broken.__orig_bases__ = (Configurable[Unbound],)  # pyright: ignore[reportAttributeAccessIssue, reportGeneralTypeIssues]


def test_lookup_parametrized_configurable():
    assert (
        instantiate({"$class": "tests.schemas.TypedEncoder", "width": "3"}).width == 3
    )


def test_lookup_through_parametrized_generic_intermediate():
    obj = instantiate({"$class": f"{__name__}.Leaf", "width": "3"})
    assert obj.fields == {"width": 3}


def test_lookup_unparametrized_generic_uses_type_variable_default():
    obj = instantiate({"$class": f"{__name__}.MidWithDefault", "width": "3"})
    assert obj.fields == {"width": 3}


def test_lookup_unparametrized_generic_without_default_has_no_schema():
    obj = instantiate({"$class": f"{__name__}.Mid", "width": "3", "other": 1})
    assert obj.fields == {"width": "3", "other": 1}


def test_lookup_generic_mixin_before_configurable_base():
    obj = instantiate({"$class": f"{__name__}.MixedIn", "width": "3"})
    assert obj.width == 3


def test_lookup_bare_configurable_has_no_schema():
    obj = instantiate({"$class": "tests.schemas.Untyped", "anything": "3"})
    assert obj.fields == {"anything": "3"}


def test_lookup_failed_substitution_raises():
    with pytest.raises(SchemaDefinitionError, match="Cannot resolve type variable"):
        check_schema(Broken)
