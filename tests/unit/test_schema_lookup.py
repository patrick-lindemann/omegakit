import pytest
from typing_extensions import TypeVar

from omegakit import Configurable, check_schema, instantiate

# Contracts: §10 Typed configs (schema lookup).

Unbound = TypeVar("Unbound")


class Broken(Configurable):
    """Claims a type variable in its bases that nothing can substitute."""


Broken.__orig_bases__ = (Configurable[Unbound],)  # pyright: ignore[reportAttributeAccessIssue, reportGeneralTypeIssues]


def test_lookup_parametrized_configurable():
    assert (
        instantiate({"$class": "tests.schemas.TypedEncoder", "width": "3"}).width == 3
    )


def test_lookup_through_parametrized_generic_intermediate():
    obj = instantiate({"$class": "tests.schemas.Leaf", "width": "3"})
    assert obj.fields == {"width": 3}


def test_lookup_unparametrized_generic_uses_type_variable_default():
    obj = instantiate({"$class": "tests.schemas.MidWithDefault", "width": "3"})
    assert obj.fields == {"width": 3}


def test_lookup_unparametrized_generic_without_default_has_no_schema():
    obj = instantiate({"$class": "tests.schemas.Mid", "width": "3", "other": 1})
    assert obj.fields == {"width": "3", "other": 1}


def test_lookup_generic_mixin_before_configurable_base():
    obj = instantiate({"$class": "tests.schemas.MixedIn", "width": "3"})
    assert obj.width == 3


def test_lookup_bare_configurable_has_no_schema():
    obj = instantiate({"$class": "tests.schemas.Untyped", "anything": "3"})
    assert obj.fields == {"anything": "3"}


def test_lookup_failed_substitution_raises():
    with pytest.raises(TypeError, match="Cannot resolve type variable"):
        check_schema(Broken)
