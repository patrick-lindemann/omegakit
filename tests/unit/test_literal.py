import pytest

from omegakit import (
    ConfigValidationError,
    generate_json_schema,
    instantiate,
    is_valid,
    validate,
)
from tests import schemas

# Contracts: §10 Typed configs, §11 Validation, §12 Editor schemas.

LITERALS = "tests.schemas.WithLiterals"


def _fields(**values):
    return instantiate({"$class": LITERALS, **values}).fields


def test_literal_defaults():
    fields = _fields()
    assert (fields["mode"], fields["level"], fields["batch"]) == ("train", 1, "auto")
    assert fields["section"] == schemas.ModeSection("fast")


def test_literal_accepts_allowed_values():
    fields = _fields(
        mode="eval",
        level=3,
        batch=16,
        maybe="b",
        modes=["x", "y"],
        section={"mode": "slow"},
        sections=[{"mode": "slow"}, {}],
    )
    assert (fields["mode"], fields["level"], fields["batch"]) == ("eval", 3, 16)
    assert (fields["maybe"], fields["modes"]) == ("b", ["x", "y"])
    assert fields["section"] == schemas.ModeSection("slow")
    assert fields["sections"] == [schemas.ModeSection("slow"), schemas.ModeSection()]


@pytest.mark.parametrize(
    ("values", "key"),
    [
        ({"mode": "test"}, "mode"),
        ({"level": 4}, "level"),
        ({"batch": "all"}, "batch"),
        ({"maybe": "c"}, "maybe"),
        ({"modes": ["x", "z"]}, r"modes\.1"),
        ({"section": {"mode": "medium"}}, r"section\.mode"),
        ({"sections": [{"mode": "medium"}]}, r"sections\.0\.mode"),
    ],
)
def test_literal_rejects_other_values_with_their_path(values, key):
    with pytest.raises(ConfigValidationError, match=rf"`{key}`"):
        _fields(**values)
    assert not is_valid({"$class": LITERALS, **values})


def test_literal_values_are_converted_like_their_type_first():
    assert _fields(level="2")["level"] == 2
    with pytest.raises(ConfigValidationError, match="`level`"):
        _fields(level=True)


def test_literal_validate_without_building():
    validate({"node": {"$class": LITERALS, "mode": "eval"}})
    with pytest.raises(ConfigValidationError, match=r"`node\.mode`"):
        validate({"node": {"$class": LITERALS, "mode": "test"}})


def test_literal_in_a_root_schema():
    validate({"mode": "eval"}, schema=schemas.LiteralConfig)
    with pytest.raises(ConfigValidationError, match="`mode`"):
        validate({"mode": "test"}, schema=schemas.LiteralConfig)


def test_literal_values_must_be_plain():
    with pytest.raises(ConfigValidationError, match="strings, integers or booleans"):
        instantiate({"$class": "tests.schemas.WithFloatLiteral"})


def test_literal_json_schema_lists_values():
    properties = generate_json_schema(schemas.LiteralConfig)["properties"]
    assert properties["mode"]["anyOf"][0] == {"enum": ["train", "eval"]}
    assert properties["level"]["anyOf"][0] == {"enum": [1, 2, 3]}
