from __future__ import annotations

import dataclasses
import enum
import typing
from collections.abc import Callable, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any, Literal, NotRequired, Required, TypedDict

import pytest
from omegaconf import MISSING
from omegaconf.errors import ConfigKeyError, MissingMandatoryValue, ValidationError

from omegakit._core.error import OmegaKitBaseException
from omegakit.configurable import Configurable
from omegakit.schema import (
    ConfigSchemaError,
    SchemaDefinitionError,
    SchemaKeyError,
    SchemaMissingValueError,
    SchemaTypeError,
    SchemaValueError,
    convert_data,
    find_schema,
    read_fields,
)


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


def test_dataclass_is_its_own_schema(targets: ModuleType):
    assert find_schema(targets.Optimizer) is targets.Optimizer


def test_configurable_names_its_schema(targets: ModuleType):
    assert find_schema(targets.Model) is targets.ModelConfig
    assert find_schema(Configurable) is None


def test_configurable_that_is_a_dataclass_is_its_own_schema(targets: ModuleType):
    assert find_schema(targets.Layer) is targets.Layer


@pytest.mark.parametrize("target", [_Encoder, len, "builtins.dict", None])
def test_other_targets_have_no_schema(target: Any):
    assert find_schema(target) is None


@pytest.mark.parametrize("schema", [dict, _Section, _Section()])
def test_schema_of_a_configurable_must_be_a_typed_dict(schema: Any):
    broken = type("Broken", (Configurable,), {"schema": schema})
    with pytest.raises(SchemaDefinitionError, match="Broken"):
        find_schema(broken)


@pytest.mark.parametrize(
    "annotation",
    [
        int,
        str,
        Path,
        _Color,
        Literal["a", "b"],
        int | None,
        int | str,
        list[int],
        dict[str, float],
        tuple[int, str],
        list[int] | None,
        Literal[[1, 2]],
    ],
)
def test_field_that_omegaconf_supports_is_data(annotation: Any):
    assert read_fields(_make_schema(annotation))["value"].is_data


@pytest.mark.parametrize(
    "annotation",
    [
        Any,
        _Encoder,
        _Encoder | None,
        _Encoder | _Color,
        list[_Encoder],
        dict[str, _Encoder],
        list[Any],
        list,
        typing.Dict,  # noqa: UP006
        typing.List | None,  # noqa: UP006
        Callable[..., _Encoder],
        type[_Encoder],
        _Section,
        _Section | None,
        list[_Section],
        dict[str, list[_Section]],
    ],
)
def test_field_that_holds_objects_is_not_data(annotation: Any):
    field = read_fields(_make_schema(annotation))["value"]
    assert not field.is_data
    assert field.annotation == annotation


@pytest.mark.parametrize(
    "annotation",
    [
        set[int],
        frozenset,
        Sequence[int],
        tuple[_Encoder, ...],
        list[set[int]],
        _Encoder | Literal["auto"],
    ],
)
def test_annotation_that_is_neither_data_nor_a_class_is_rejected(annotation: Any):
    with pytest.raises(SchemaDefinitionError, match=r"Schema\.value"):
        read_fields(_make_schema(annotation))


def test_annotation_that_does_not_resolve_is_rejected():
    with pytest.raises(SchemaDefinitionError, match="NoSuchName") as error_info:
        read_fields(_make_schema("NoSuchName"))
    assert isinstance(error_info.value.__cause__, NameError)


def test_fields_are_the_arguments_of_the_constructor(targets: ModuleType):
    fields = read_fields(targets.Optimizer)
    assert "total" not in fields
    assert fields["lr"].is_required
    assert not fields["steps"].is_required
    assert not read_fields(targets.Experiment)["optimizer"].is_required


def test_keys_of_a_typed_dict_are_required_unless_marked():
    fields = read_fields(_WideLayerConfig)
    required_keys = {key for key, field in fields.items() if field.is_required}
    assert set(fields) == {"width", "bias", "encoder", "scale", "name"}
    assert required_keys == {"width", "name"}
    assert fields["width"].is_data
    assert fields["bias"].annotation is bool
    assert not fields["encoder"].is_data


def test_field_that_holds_a_typed_dict_is_not_data():
    fields = read_fields(_NetworkConfig)
    assert not fields["layer"].is_data
    assert not fields["layers"].is_data


def test_union_of_two_typed_dicts_is_rejected():
    with pytest.raises(SchemaDefinitionError, match=r"Schema\.value"):
        read_fields(_make_schema(_LayerConfig | _NetworkConfig | None))
    assert not read_fields(_make_schema(_LayerConfig | _Encoder))["value"].is_data


@pytest.mark.parametrize("key", ["learning-rate", "class", "2nd"])
def test_key_that_is_no_identifier_is_rejected(key: str):
    schema = TypedDict("schema", {key: int})  # pyright: ignore[reportGeneralTypeIssues]
    with pytest.raises(SchemaDefinitionError, match=key):
        read_fields(schema)


def test_default_that_is_missing_marks_a_required_field():
    schema = dataclasses.make_dataclass("Schema", [("value", int, MISSING)])
    assert read_fields(schema)["value"].is_required


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
    with pytest.raises(SchemaValueError, match="Optimizer") as error_info:
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
    with pytest.raises(SchemaValueError):
        convert_data(targets.Optimizer, {"lr": text})
    with pytest.raises(SchemaValueError):
        convert_data(targets.Optimizer, {"betas": [0.5, text]})


def test_number_that_is_too_large_is_rejected(targets: ModuleType):
    with pytest.raises(SchemaValueError, match="Optimizer"):
        convert_data(targets.Optimizer, {"lr": 10**400})


@pytest.mark.parametrize(
    ("error_type", "parent_type"),
    [
        (SchemaDefinitionError, TypeError),
        (SchemaKeyError, ConfigKeyError),
        (SchemaMissingValueError, MissingMandatoryValue),
        (SchemaValueError, ValidationError),
        (SchemaTypeError, ValidationError),
    ],
)
def test_errors_are_also_builtin_or_omegaconf_errors(
    error_type: type[Exception], parent_type: type[Exception]
):
    assert issubclass(error_type, ConfigSchemaError)
    assert issubclass(error_type, OmegaKitBaseException)
    assert issubclass(error_type, parent_type)
