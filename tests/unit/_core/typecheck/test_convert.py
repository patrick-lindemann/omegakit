from __future__ import annotations

import dataclasses
import enum
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from typing_extensions import TypeAliasType

from omegakit._core.errors import (
    ConfigSchemaError,
)
from omegakit._core.typecheck.convert import convert_plain_values, convert_value


class _Color(enum.Enum):
    RED = "red"
    BLUE = "blue"


_Size = TypeAliasType("_Size", int)


def test_plain_values_are_converted_as_omegaconf_converts_them(targets: ModuleType):
    values = {
        "lr": "1e-3",
        "mode": "slow",
        "betas": [0.5, "0.75"],
        "log_dir": "runs/first",
    }
    converted = convert_plain_values(targets.Optimizer, values, "")
    assert converted == {
        "lr": 0.001,
        "mode": targets.Mode.SLOW,
        "betas": (0.5, 0.75),
        "log_dir": Path("runs/first"),
    }
    assert type(converted["betas"]) is tuple
    assert targets.CALLS == []


@pytest.mark.parametrize(
    ("values", "key"),
    [
        ({"lr": "fast"}, "lr"),
        ({"mode": "medium"}, "mode"),
        ({"betas": [0.5, 0.75, 0.9]}, "betas"),
        ({"betas": [0.5, "high"]}, "betas"),
    ],
)
def test_plain_value_that_does_not_match_is_rejected(
    targets: ModuleType, values: dict[str, Any], key: str
):
    with pytest.raises(ConfigSchemaError, match="Optimizer") as error_info:
        convert_plain_values(targets.Optimizer, values, "optimizer")
    assert error_info.value.full_key == f"optimizer.{key}"


def test_plain_value_of_the_root_is_named_by_its_own_key(targets: ModuleType):
    with pytest.raises(ConfigSchemaError) as error_info:
        convert_plain_values(targets.Optimizer, {"lr": "fast"}, "")
    assert error_info.value.full_key == "lr"


@pytest.mark.parametrize(
    "text", ["${lr}", "a\\${lr}", "\\\\${lr} and ${steps}", "${open", "???", "\\???"]
)
def test_text_is_not_read_as_an_interpolation_or_a_missing_value(
    targets: ModuleType, text: str
):
    schema = dataclasses.make_dataclass(
        "Schema", [("name", str), ("names", dict[str, list[str]]), ("lr", float)]
    )
    values = {"name": text, "names": {"first": [text, "plain"]}, "lr": 1}
    converted = convert_plain_values(schema, values, "")
    assert converted["name"] == text
    assert converted["names"] == {"first": [text, "plain"]}
    with pytest.raises(ConfigSchemaError):
        convert_plain_values(targets.Optimizer, {"lr": text}, "")
    with pytest.raises(ConfigSchemaError):
        convert_plain_values(targets.Optimizer, {"betas": [0.5, text]}, "")


def test_item_is_converted_as_its_annotation():
    assert convert_value(float, "0.5") == 0.5
    assert convert_value(_Color, "RED") is _Color.RED
    with pytest.raises(ConfigSchemaError):
        convert_value(float, "high")


def test_alias_of_typing_extensions_is_converted_as_its_value():
    schema = dataclasses.make_dataclass("Schema", [("size", _Size)])
    assert convert_plain_values(schema, {"size": "3"}, "") == {"size": 3}
    assert convert_value(list[_Size], ["1", 2]) == [1, 2]
    with pytest.raises(ConfigSchemaError):
        convert_value(_Size, "big")


def test_number_that_is_too_large_is_rejected(targets: ModuleType):
    with pytest.raises(ConfigSchemaError, match="Optimizer"):
        convert_plain_values(targets.Optimizer, {"lr": 10**400}, "")
