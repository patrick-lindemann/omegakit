from dataclasses import InitVar, dataclass, field
from typing import Any

import pytest
from omegaconf import OmegaConf

from omegakit import Configurable, ConfigValidationError, instantiate, validate
from tests import schemas

# Contracts: §10 Typed configs (field kinds), §11 Validation.


@dataclass
class InitVarConfig:
    value: int = 0
    seed: InitVar[int] = 0


class WithInitVar(Configurable[InitVarConfig]):
    def __init__(self, **fields: Any) -> None:
        self.fields = fields


@dataclass(kw_only=True)
class KwOnlyConfig:
    value: int = 0


class KwOnly(Configurable[KwOnlyConfig]):
    def __init__(self, **fields: Any) -> None:
        self.fields = fields


TYPES = "tests.schemas.Types"
CONTAINERS = "tests.schemas.ObjectContainers"


def _fields(**values):
    return instantiate({"$class": TYPES, **values}).fields


def test_types_defaults():
    fields = _fields()
    assert (fields["pair"], fields["numbers"]) == ((0, "a"), ())
    assert fields["sub_default"] == schemas.Sub()
    assert fields["point"] == {"x": 0}


def test_types_tuples():
    fields = _fields(pair=["1", 2], numbers=["1", 2])
    assert fields["pair"] == (1, "2")
    assert fields["numbers"] == (1, 2)
    with pytest.raises(ConfigValidationError, match=r"`pair` expects a list of 2"):
        _fields(pair=[1])
    with pytest.raises(ConfigValidationError, match=r"`pair\.0`"):
        _fields(pair=["x", "y"])


def test_types_tuples_reject_extra_items():
    with pytest.raises(ConfigValidationError, match=r"`pair` expects a list of 2"):
        validate({"$class": TYPES, "pair": [1, "a", 3]})
    with pytest.raises(ConfigValidationError, match=r"`pair` expects a list of 2"):
        _fields(pair=[1, "a", 3])


def test_types_abstract_containers_give_lists_and_dicts():
    fields = _fields(sequence=["1"], mapping={"a": "2"})
    assert (fields["sequence"], fields["mapping"]) == ([1], {"a": 2})


def test_types_typed_dict_fields_are_unchecked_dicts():
    assert _fields(point={"x": "a", "extra": [1]})["point"] == {"x": "a", "extra": [1]}


def test_types_enums_by_name_or_value():
    fields = _fields(color="blue", level=2, colors={"red": 1, "BLUE": 2})
    assert fields["color"] is schemas.Color.BLUE
    assert fields["level"] is schemas.Level.HIGH
    assert fields["colors"] == {schemas.Color.RED: 1, schemas.Color.BLUE: 2}


def test_types_enum_names_win_over_values():
    assert _fields(clash="B")["clash"] is schemas.Clash.B
    assert _fields(clash="x")["clash"] is schemas.Clash.B


@pytest.mark.parametrize(("key", "value"), [("level", True), ("level", "2")])
def test_types_enum_values_need_their_exact_type(key, value):
    with pytest.raises(ConfigValidationError, match=f"`{key}`"):
        _fields(**{key: value})


def test_types_union_with_a_dataclass():
    assert _fields(sub_or_int={"value": "2"})["sub_or_int"] == schemas.Sub(2)
    assert _fields(sub_or_int=5)["sub_or_int"] == 5
    assert _fields(sub_default=5)["sub_default"] == 5
    assert _fields(maybe_sub={"value": 1})["maybe_sub"] == schemas.Sub(1)


@pytest.mark.parametrize("value", ["5", 5.5, True, [1]])
def test_types_union_scalars_need_an_exact_type(value):
    with pytest.raises(ConfigValidationError, match="`sub_or_int`"):
        _fields(sub_or_int=value)


def test_types_union_rejects_null_without_none():
    assert _fields(maybe_sub=None)["maybe_sub"] is None
    with pytest.raises(ConfigValidationError, match="`sub_or_int`"):
        validate({"$class": TYPES, "sub_or_int": None})
    with pytest.raises(ConfigValidationError, match="`sub_or_int`"):
        _fields(sub_or_int=None)


def test_types_union_with_a_list():
    assert _fields(list_or_int=["1", 2])["list_or_int"] == [1, 2]
    assert _fields(list_or_int=3)["list_or_int"] == 3
    with pytest.raises(ConfigValidationError, match="`list_or_int`"):
        _fields(list_or_int={"a": 1})


def test_types_init_false_fields_are_not_configurable():
    obj = instantiate({"$class": "tests.schemas.InitFalse", "value": 2})
    assert obj.fields == {"value": 2}
    with pytest.raises(ConfigValidationError, match=r"Unknown field.*'derived'"):
        instantiate({"$class": "tests.schemas.InitFalse", "derived": 1})


def test_types_init_var_with_default_and_keyword_only_fields():
    assert instantiate({"$class": f"{__name__}.WithInitVar"}).fields == {"value": 0}
    with pytest.raises(ConfigValidationError, match=r"Unknown field.*'seed'"):
        instantiate({"$class": f"{__name__}.WithInitVar", "seed": 1})
    assert instantiate({"$class": f"{__name__}.KwOnly", "value": 3}).fields == {
        "value": 3
    }


def test_types_object_containers_build_every_item():
    fields = instantiate(
        {
            "$class": CONTAINERS,
            "encoders": [{"$class": "tests.schemas.Encoder", "width": 2}],
            "by_name": {"a": {"$class": "tests.schemas.Encoder", "width": 3}},
            "sections": [{"encoder": {"$class": "tests.schemas.Encoder"}}],
            "maybe": None,
        }
    ).fields
    assert fields["encoders"][0].width == 2
    assert fields["by_name"]["a"].width == 3
    assert isinstance(fields["sections"][0], schemas.SectionWithObject)
    assert fields["maybe"] is None


def test_types_object_containers_check_every_item():
    wrong = {"$class": CONTAINERS, "encoders": [{"$class": "tests.schemas.Decoder"}]}
    with pytest.raises(ConfigValidationError, match=r"`encoders\.0` expects Encoder"):
        validate(wrong)
    with pytest.raises(ConfigValidationError, match="`by_name` expects"):
        validate({"$class": CONTAINERS, "by_name": [1]})


def test_types_behave_the_same_through_validate():
    validate(OmegaConf.create({"$class": TYPES, "color": "blue", "pair": [1, "a"]}))
    with pytest.raises(ConfigValidationError, match="`sub_or_int`"):
        validate({"$class": TYPES, "sub_or_int": "5"})


@dataclass
class OptionalsConfig:
    numbers: list[int] | None = None
    counts: dict[str, int] | None = None
    sub: schemas.Sub | None = None


class Optionals(Configurable[OptionalsConfig]):
    def __init__(self, **fields: Any) -> None:
        self.fields = fields


OPTIONALS = f"{__name__}.Optionals"


def test_types_optional_containers_and_dataclasses():
    fields = instantiate(
        {"$class": OPTIONALS, "numbers": ["1"], "counts": {"a": "2"}, "sub": {}}
    ).fields
    assert fields == {"numbers": [1], "counts": {"a": 2}, "sub": schemas.Sub()}
    assert instantiate({"$class": OPTIONALS, "numbers": None}).fields["numbers"] is None


# OmegaConf 2.4 does not name the field when a dataclass gets a scalar.
@pytest.mark.parametrize(
    ("key", "value", "match"),
    [
        ("numbers", "abc", "`numbers"),
        ("numbers", 5, "`numbers"),
        ("numbers", ["x"], "`numbers"),
        ("counts", "abc", "`counts"),
        ("counts", {"a": "x"}, "`counts"),
        ("sub", 5, "Sub"),
        ("sub", {"value": "x"}, "`sub"),
    ],
)
def test_types_optional_containers_and_dataclasses_reject_other_values(
    key, value, match
):
    config = {"$class": OPTIONALS, key: value}
    with pytest.raises(ConfigValidationError, match=match):
        validate(config)
    with pytest.raises(ConfigValidationError, match=match):
        instantiate(config)


@dataclass
class ListUnionConfig:
    value: int | list[int] = 0
    maybe: int | list[int] | None = 0


class ListUnion(Configurable[ListUnionConfig]):
    def __init__(self, **fields: Any) -> None:
        self.fields = fields


LIST_UNION = f"{__name__}.ListUnion"


def test_types_list_union_accepts_its_members():
    fields = instantiate({"$class": LIST_UNION, "value": [1], "maybe": None}).fields
    assert fields == {"value": [1], "maybe": None}


@pytest.mark.parametrize("value", ["wrong", 3.5, True, None])
def test_types_list_union_rejects_other_scalars(value):
    with pytest.raises(ConfigValidationError, match="`value`"):
        validate({"$class": LIST_UNION, "value": value})
    with pytest.raises(ConfigValidationError, match="`value`"):
        instantiate({"$class": LIST_UNION, "value": value})


@dataclass
class Doubling:
    x: int = 1

    def __post_init__(self) -> None:
        self.x *= 2


@dataclass
class DoublingHolder:
    doubling: Doubling = field(default_factory=Doubling)


@dataclass
class DefaultsConfig:
    doubling: Doubling = field(default_factory=Doubling)
    holder: DoublingHolder = field(default_factory=DoublingHolder)


class Defaults(Configurable[DefaultsConfig]):
    def __init__(self, **fields: Any) -> None:
        self.fields = fields


DEFAULTS = f"{__name__}.Defaults"


def test_types_default_dataclasses_are_built_once():
    fields = instantiate({"$class": DEFAULTS}).fields
    assert fields["doubling"].x == 2
    assert fields["holder"].doubling.x == 2
    assert instantiate({"$class": DEFAULTS, "holder": {}}).fields["holder"] == (
        DoublingHolder()
    )
    given = {"$class": DEFAULTS, "holder": {"doubling": {"x": 3}}}
    assert instantiate(given).fields["holder"].doubling.x == 6
