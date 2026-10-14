from __future__ import annotations

import dataclasses
import enum
from pathlib import Path
from types import ModuleType
from typing import Any, NotRequired, Required, TypedDict

import pytest

from omegakit._core.errors import (
    ConfigSchemaError,
)
from omegakit._core.schema.convert import convert_data, convert_item


class _Color(enum.Enum):
    RED = "red"
    BLUE = "blue"


class _Encoder:
    pass


@dataclasses.dataclass
class _Section:
    width: int = 1


class _LayerConfig(TypedDict):
    width: int
    bias: NotRequired[bool]
    encoder: NotRequired[_Encoder | None]


class _WideLayerConfig(_LayerConfig, total=False):
    scale: float
    name: Required[str]


class _NetworkConfig(TypedDict):
    layer: _LayerConfig
    layers: list[_LayerConfig]


def _make_schema(annotation: Any) -> type:
    return dataclasses.make_dataclass("Schema", [("value", annotation)])


def test_data_is_converted_as_omegaconf_converts_it(targets: ModuleType):
    values = {
        "lr": "1e-3",
        "mode": "slow",
        "betas": [0.5, "0.75"],
        "log_dir": "runs/first",
    }
    converted = convert_data(targets.Optimizer, values)
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
def test_data_that_does_not_match_is_rejected(
    targets: ModuleType, values: dict[str, Any], key: str
):
    with pytest.raises(ConfigSchemaError, match="Optimizer") as error_info:
        convert_data(targets.Optimizer, values)
    assert key in str(error_info.value)


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
    converted = convert_data(schema, values)
    assert converted["name"] == text
    assert converted["names"] == {"first": [text, "plain"]}
    with pytest.raises(ConfigSchemaError):
        convert_data(targets.Optimizer, {"lr": text})
    with pytest.raises(ConfigSchemaError):
        convert_data(targets.Optimizer, {"betas": [0.5, text]})


def test_item_is_converted_as_its_annotation():
    assert convert_item(float, "0.5") == 0.5
    assert convert_item(_Color, "RED") is _Color.RED
    with pytest.raises(ConfigSchemaError):
        convert_item(float, "high")


def test_number_that_is_too_large_is_rejected(targets: ModuleType):
    with pytest.raises(ConfigSchemaError, match="Optimizer"):
        convert_data(targets.Optimizer, {"lr": 10**400})
