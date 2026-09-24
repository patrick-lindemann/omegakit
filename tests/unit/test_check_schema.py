import pytest

from omegakit import ConfigValidationError, check_schema, instantiate
from tests import schemas

# Contracts: §10 Typed configs (consistency check).


def test_check_schema_accepts_matching_class():
    check_schema(schemas.TypedEncoder)


def test_check_schema_required_parameter_needs_a_field():
    with pytest.raises(ConfigValidationError, match="required parameter `z`"):
        check_schema(schemas.MissingParameter)


def test_check_schema_extra_field_needs_kwargs():
    with pytest.raises(ConfigValidationError, match="Field `y`"):
        check_schema(schemas.ExtraField)
    check_schema(schemas.ExtraFieldWithKwargs)


def test_check_schema_int_field_is_assignable_to_float():
    check_schema(schemas.FloatParameters)


def test_check_schema_rejects_unassignable_annotation():
    with pytest.raises(ConfigValidationError, match="not assignable"):
        check_schema(schemas.StrParameter)


def test_check_schema_subclass_field_is_assignable_to_base():
    check_schema(schemas.TakesBase)


def test_check_schema_optional_field_is_not_assignable_to_required():
    with pytest.raises(ConfigValidationError, match="not assignable"):
        check_schema(schemas.NeedsEncoder)


def test_check_schema_skips_generic_annotations():
    check_schema(schemas.GenericParameter)


def test_check_schema_skips_custom_from_config():
    check_schema(schemas.CustomFromConfig)
    assert instantiate({"$class": "tests.schemas.CustomFromConfig", "x": 1}).z == 1


def test_check_schema_ignores_classes_without_schema():
    check_schema(schemas.Untyped)
    check_schema(schemas.Encoder)


def test_check_schema_runs_before_children_are_built():
    with pytest.raises(ConfigValidationError, match="required parameter `z`"):
        instantiate(
            {
                "$class": "tests.schemas.MissingParameter",
                "x": {"$class": "tests.helpers.Failing"},
            }
        )
