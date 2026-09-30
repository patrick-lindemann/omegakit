from typing import Any

import pytest

from omegakit import (
    Configurable,
    ConfigValidationError,
    instantiate,
    validate,
)
from tests import schemas
from tests.schemas import LiteralConfig


class WithLiterals(Configurable):
    schema = LiteralConfig

    def __init__(self, **fields: Any) -> None:
        self.fields = fields


LITERALS = f"{__name__}.WithLiterals"


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
    ],
)
def test_literal_rejects_other_values_with_their_path(values, key):
    with pytest.raises(ConfigValidationError, match=rf"`{key}`"):
        _fields(**values)


@pytest.mark.parametrize("level", ["2", True])
def test_literal_values_need_their_exact_value(level):
    with pytest.raises(ConfigValidationError, match="`level`"):
        _fields(level=level)


def test_literal_validate_without_building():
    validate({"node": {"$class": LITERALS, "mode": "eval"}})
    with pytest.raises(ConfigValidationError, match=r"`node\.mode`"):
        validate({"node": {"$class": LITERALS, "mode": "test"}})


def test_literal_in_a_root_schema():
    validate({"mode": "eval"}, schema=schemas.LiteralConfig)
    with pytest.raises(ConfigValidationError, match="`mode`"):
        validate({"mode": "test"}, schema=schemas.LiteralConfig)
