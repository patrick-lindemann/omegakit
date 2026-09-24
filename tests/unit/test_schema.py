from pathlib import Path

import pytest
from omegaconf import OmegaConf

from omegakit import ConfigValidationError, check_schema, instantiate, prepare
from tests import schemas

# Contracts: §10 Typed configs (field kinds, supported subset, validation).

FIELDS = "tests.schemas.Fields"
ENCODER = "tests.schemas.Encoder"


def test_schema_native_values_are_coerced():
    obj = instantiate({"$class": FIELDS, "count": "3", "path": "a/b"})
    assert obj.fields["count"] == 3
    assert obj.fields["path"] == Path("a/b")


def test_schema_defaults_fill_absent_fields():
    obj = instantiate({"$class": FIELDS})
    assert obj.fields["count"] == 0
    assert obj.fields["encoder"] is None


def test_schema_enum_given_by_member_name():
    assert instantiate({"$class": FIELDS, "kind": "B"}).fields["kind"] is schemas.Kind.B


def test_schema_enum_value_is_rejected():
    with pytest.raises(ConfigValidationError, match="alpha"):
        instantiate({"$class": FIELDS, "kind": "alpha"})


def test_schema_union_of_primitives_is_not_coerced():
    assert instantiate({"$class": FIELDS, "number": "x"}).fields["number"] == "x"
    with pytest.raises(ConfigValidationError):
        instantiate({"$class": FIELDS, "number": 1.5})


def test_schema_nested_dataclasses_are_rebuilt_as_user_classes():
    obj = instantiate(
        {
            "$class": FIELDS,
            "sub": {"value": 1},
            "subs": [{"value": 2}],
            "by_name": {"a": {"value": 3}},
        }
    )
    assert obj.fields["sub"] == schemas.Sub(1, 2)
    assert obj.fields["subs"] == [schemas.Sub(2, 4)]
    assert obj.fields["by_name"] == {"a": schemas.Sub(3, 6)}


def test_schema_object_field_is_built():
    obj = instantiate({"$class": FIELDS, "encoder": {"$class": ENCODER, "width": 4}})
    assert isinstance(obj.fields["encoder"], schemas.Encoder)
    assert obj.fields["encoder"].width == 4


def test_schema_object_field_of_wrong_type_raises_with_path():
    with pytest.raises(
        ConfigValidationError, match=r"`point\.encoder`.*Encoder \| None.*Decoder"
    ):
        instantiate(
            {
                "$class": "tests.helpers.Container",
                "name": "c",
                "point": {
                    "$class": FIELDS,
                    "encoder": {"$class": "tests.schemas.Decoder"},
                },
            }
        )


def test_schema_object_field_rejects_plain_mapping():
    with pytest.raises(ConfigValidationError, match="dict"):
        instantiate({"$class": FIELDS, "encoder": {"width": 4}})


def test_schema_isinstance_check_unwraps_aliases():
    with pytest.raises(ConfigValidationError, match="Decoder"):
        instantiate({"$class": FIELDS, "aliased": {"$class": "tests.schemas.Decoder"}})


def test_schema_isinstance_check_skipped_for_partials():
    obj = instantiate(
        {"$class": FIELDS, "encoder": {"$class": ENCODER, "$partial": True}}
    )
    assert obj.fields["encoder"](width=2).width == 2


def test_schema_isinstance_check_skipped_for_generic_annotations():
    obj = instantiate({"$class": FIELDS, "factory": {"$ref": ENCODER}})
    assert obj.fields["factory"] is schemas.Encoder


def test_schema_isinstance_check_skipped_for_non_runtime_protocols():
    obj = instantiate({"$class": FIELDS, "greeter": {"$class": ENCODER}})
    assert isinstance(obj.fields["greeter"], schemas.Encoder)


def test_schema_any_field_accepts_resolver_objects():
    OmegaConf.register_new_resolver("obj", lambda: schemas.Encoder(5))
    obj = instantiate(OmegaConf.create({"$class": FIELDS, "anything": "${obj:}"}))
    assert obj.fields["anything"].width == 5


def test_schema_any_field_builds_nested_classes():
    obj = instantiate(
        {"$class": FIELDS, "anything": {"inner": {"$class": ENCODER, "width": 2}}}
    )
    assert obj.fields["anything"]["inner"].width == 2


def test_schema_object_default_never_enters_omegaconf():
    obj = instantiate(
        {"$class": "tests.schemas.RequiredObject", "encoder": {"$class": ENCODER}}
    )
    assert isinstance(obj.encoder, schemas.Encoder)


def test_schema_unknown_field_raises():
    with pytest.raises(ConfigValidationError, match="'colour'"):
        instantiate({"$class": FIELDS, "colour": "red"})


def test_schema_missing_required_native_field_raises():
    with pytest.raises(ConfigValidationError, match="depth"):
        instantiate({"$class": "tests.schemas.Model"})


def test_schema_missing_required_object_field_raises():
    with pytest.raises(ConfigValidationError, match="Missing required field `encoder`"):
        instantiate({"$class": "tests.schemas.RequiredObject"})


def test_schema_wrong_native_type_raises_with_path_and_schema_name():
    with pytest.raises(ConfigValidationError, match=r"`point`.*FieldsConfig"):
        instantiate(
            {
                "$class": "tests.helpers.Container",
                "name": "c",
                "point": {"$class": FIELDS, "count": "many"},
            }
        )


def test_schema_class_node_in_native_field_raises():
    with pytest.raises(ConfigValidationError, match=r"\$class"):
        instantiate({"$class": FIELDS, "sub": {"$class": ENCODER}})


def test_schema_validation_happens_at_prepare():
    with pytest.raises(ConfigValidationError):
        prepare({"$class": FIELDS, "count": "many"})


@pytest.mark.parametrize(
    ("cls", "match"),
    [
        (schemas.InitFalse, "init=False"),
        (schemas.WithInitVar, "InitVar"),
        (schemas.KwOnly, "keyword-only"),
        (schemas.WithTuple, "unsupported container"),
        (schemas.WithSet, "unsupported container"),
        (schemas.WithObjectList, "Use `Any`"),
        (schemas.WithMixedUnion, "mixes value types and classes"),
        (schemas.WithUnresolvable, "field `value`"),
        (schemas.WithDataclassUnion, "cannot be validated by OmegaConf"),
    ],
)
def test_schema_outside_supported_subset_raises(cls, match):
    with pytest.raises(ConfigValidationError, match=match):
        check_schema(cls)
