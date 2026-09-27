import sys
import types
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any, ClassVar

import pytest
from omegaconf import OmegaConf

from omegakit import (
    Configurable,
    ConfigValidationError,
    SchemaDefinitionError,
    check_schema,
    instantiate,
    prepare,
    validate,
)
from omegakit.utils import register_resolver
from tests import schemas
from tests.schemas import Encoder, EncoderConfig, SectionWithObject, Sub


@dataclass
class SetConfig:
    values: set[int] = field(default_factory=set)


class WithSet(Configurable[SetConfig]):
    def __init__(self, **fields: Any) -> None: ...


@dataclass
class MixedUnionConfig:
    value: int | Encoder = 0


class WithMixedUnion(Configurable[MixedUnionConfig]):
    def __init__(self, **fields: Any) -> None: ...


@dataclass
class UnresolvableConfig:
    value: "Missing" = None  # type: ignore[name-defined]  # noqa: F821


class WithUnresolvable(Configurable[UnresolvableConfig]):
    def __init__(self, **fields: Any) -> None: ...


@dataclass
class HolderConfig:
    section: SectionWithObject | None = None


class Holder(Configurable[HolderConfig]):
    def __init__(self, section: SectionWithObject | None) -> None:
        self.section = section


@dataclass
class AmbiguousUnionConfig:
    value: Sub | EncoderConfig | None = None


class WithAmbiguousUnion(Configurable[AmbiguousUnionConfig]):
    def __init__(self, **fields: Any) -> None: ...


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


def test_schema_enum_value_is_accepted():
    assert (
        instantiate({"$class": FIELDS, "kind": "alpha"}).fields["kind"]
        is schemas.Kind.A
    )


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


def test_schema_object_field_rejects_plain_mapping():
    with pytest.raises(ConfigValidationError, match="mapping without `\\$class`"):
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
    register_resolver("obj", lambda: schemas.Encoder(5))
    obj = instantiate(OmegaConf.create({"$class": FIELDS, "anything": "${obj:}"}))
    assert obj.fields["anything"].width == 5


def test_schema_any_field_builds_nested_classes():
    obj = instantiate(
        {"$class": FIELDS, "anything": {"inner": {"$class": ENCODER, "width": 2}}}
    )
    assert obj.fields["anything"]["inner"].width == 2


@dataclass
class ObjectDefaultConfig:
    encoder: schemas.Encoder = field(default_factory=lambda: schemas.Encoder(width=3))


class WithObjectDefault(Configurable[ObjectDefaultConfig]):
    def __init__(self, encoder: schemas.Encoder) -> None:
        self.encoder = encoder


def test_schema_object_default_never_enters_omegaconf():
    config = {"$class": f"{__name__}.WithObjectDefault"}
    validate(config)
    assert instantiate(config).encoder.width == 3


def test_schema_unknown_field_raises():
    with pytest.raises(ConfigValidationError, match="colour"):
        instantiate({"$class": FIELDS, "colour": "red"})


def test_schema_missing_required_native_field_raises():
    with pytest.raises(ConfigValidationError, match="depth"):
        instantiate({"$class": "tests.schemas.Model"})


def test_schema_missing_required_object_field_raises():
    with pytest.raises(ConfigValidationError, match="Missing required field `encoder`"):
        instantiate({"$class": "tests.schemas.RequiredObject"})


def test_schema_wrong_native_type_raises_with_path_and_schema_name():
    with pytest.raises(ConfigValidationError, match=r"`point\.count`.*FieldsConfig"):
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
        (WithSet, "unsupported container"),
        (WithMixedUnion, "mixes value types and classes"),
        (WithUnresolvable, "field `value`"),
        (WithAmbiguousUnion, "cannot be told apart"),
    ],
)
def test_schema_outside_supported_subset_raises(cls, match):
    with pytest.raises(SchemaDefinitionError, match=match):
        check_schema(cls)


def test_schema_plain_mapping_in_dataclass_field_is_built_as_a_section():
    holder = instantiate(
        {
            "$class": f"{__name__}.Holder",
            "section": {"encoder": {"$class": "tests.schemas.Encoder", "width": 3}},
        },
        schema=Holder,
    )
    assert isinstance(holder.section, schemas.SectionWithObject)
    assert isinstance(holder.section.encoder, schemas.Encoder)
    assert (holder.section.encoder.width, holder.section.size) == (3, 1)


@dataclass
class InheritedBase:
    amount: "Decimal" = Decimal(0)


SUBCLASS_MODULE = """
from dataclasses import dataclass

@dataclass
class Subclass(InheritedBase):
    other: "Missing" = 0
"""


def test_schema_unresolvable_annotation_blames_its_own_field(monkeypatch):
    module = types.ModuleType("inherited_schema")
    module.InheritedBase = InheritedBase  # pyright: ignore[reportAttributeAccessIssue]
    monkeypatch.setitem(sys.modules, module.__name__, module)
    exec(SUBCLASS_MODULE, vars(module))
    with pytest.raises(SchemaDefinitionError, match="field `other`"):
        validate({}, schema=module.Subclass)


@dataclass
class Tree:
    child: "Tree | None" = None


@dataclass
class Outer:
    inner: "list[Inner]"


@dataclass
class Inner:
    outer: Outer | None = None


class WithTree(Configurable[Tree]):
    def __init__(self, child: Tree | None = None) -> None: ...


@pytest.mark.parametrize(
    ("schema", "cycle"),
    [(Tree, "Tree -> Tree"), (Outer, "Outer -> Inner -> Outer")],
)
def test_schema_recursive_dataclasses_raise(schema, cycle):
    with pytest.raises(SchemaDefinitionError, match=cycle):
        validate({}, schema=schema)


def test_schema_recursive_schema_of_a_class_raises():
    with pytest.raises(SchemaDefinitionError, match="Tree -> Tree"):
        check_schema(WithTree)


@dataclass
class Later:
    value: int = 0


@dataclass
class ForwardReferences:
    count: int = 0
    later: "Later" = field(default_factory=Later)
    missing: "Missing" = 0  # noqa: F821  # pyright: ignore[reportUndefinedVariable]


@dataclass
class UnresolvableClassVar:
    registry: ClassVar["Missing"]  # noqa: F821  # pyright: ignore[reportUndefinedVariable]
    count: int = 0


def test_schema_forward_reference_that_does_not_resolve_names_its_field():
    with pytest.raises(
        SchemaDefinitionError, match=r"field `missing`.*Import the type at module level"
    ):
        validate({}, schema=ForwardReferences)


def test_schema_annotation_outside_the_fields_that_does_not_resolve_raises():
    with pytest.raises(SchemaDefinitionError, match="Cannot resolve the annotations"):
        validate({}, schema=UnresolvableClassVar)
