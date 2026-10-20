from __future__ import annotations

import dataclasses
import enum
import typing
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Literal, TypedDict

import pytest
import typing_extensions
from omegaconf import MISSING
from typing_extensions import NotRequired, Required

from omegakit._core.configurable import Configurable
from omegakit._core.errors import (
    SchemaDefinitionError,
)
from omegakit._core.typecheck.fields import find_schema, read_fields


class _Color(enum.Enum):
    RED = "red"
    BLUE = "blue"


class _Encoder:
    pass


_Size = typing_extensions.TypeAliasType("_Size", int)


@dataclass
class _Section:
    width: int = 1


class _LayerConfig(TypedDict):
    width: int
    bias: NotRequired[bool]
    encoder: NotRequired[_Encoder | None]


class _WideLayerConfig(_LayerConfig, total=False):
    scale: float
    name: Required[str]


class _BackportedLayerConfig(typing_extensions.TypedDict):
    width: int
    bias: NotRequired[bool]
    encoder: NotRequired[_Encoder | None]


class _BackportedWideLayerConfig(_BackportedLayerConfig, total=False):
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


def test_configurable_may_name_a_typed_dict_of_typing_extensions():
    model = type("Model", (Configurable,), {"schema": _BackportedLayerConfig})
    assert find_schema(model) is _BackportedLayerConfig


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
        Literal[[1, 2]],  # ty: ignore[invalid-type-form]
        _Size,
        list[_Size] | None,
    ],
)
def test_field_that_omegaconf_supports_is_a_plain_value(annotation: Any):
    assert read_fields(_make_schema(annotation))["value"].is_plain_value


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
        tuple[_Encoder, ...],
        tuple[_Encoder, float],
        tuple[_LayerConfig, ...] | None,
    ],
)
def test_field_that_holds_objects_is_no_plain_value(annotation: Any):
    field = read_fields(_make_schema(annotation))["value"]
    assert not field.is_plain_value
    assert field.annotation == annotation


@pytest.mark.parametrize(
    "annotation",
    [
        set[int],
        frozenset,
        Sequence[int],
        tuple[_Encoder, set[int]],
        list[set[int]],
        _Encoder | Literal["auto"],
    ],
)
def test_annotation_that_is_neither_a_plain_value_nor_a_class_is_rejected(
    annotation: Any,
):
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


@pytest.mark.parametrize(
    "schema",
    [_WideLayerConfig, _BackportedWideLayerConfig],
    ids=["typing", "typing_extensions"],
)
def test_keys_of_a_typed_dict_are_required_unless_marked(schema: type):
    fields = read_fields(schema)
    required_keys = {key for key, field in fields.items() if field.is_required}
    assert set(fields) == {"width", "bias", "encoder", "scale", "name"}
    assert required_keys == {"width", "name"}
    assert fields["width"].is_plain_value
    assert fields["bias"].annotation is bool
    assert not fields["encoder"].is_plain_value


def test_field_that_holds_a_typed_dict_is_no_plain_value():
    fields = read_fields(_NetworkConfig)
    assert not fields["layer"].is_plain_value
    assert not fields["layers"].is_plain_value


def test_union_of_two_typed_dicts_is_rejected():
    with pytest.raises(SchemaDefinitionError, match=r"Schema\.value"):
        read_fields(_make_schema(_LayerConfig | _NetworkConfig | None))
    assert not read_fields(_make_schema(_LayerConfig | _Encoder))[
        "value"
    ].is_plain_value


@pytest.mark.parametrize("key", ["learning-rate", "class", "2nd"])
def test_key_that_is_no_identifier_is_rejected(key: str):
    schema = TypedDict("schema", {key: int})  # ty: ignore[invalid-argument-type]
    with pytest.raises(SchemaDefinitionError, match=key):
        read_fields(schema)


def test_default_that_is_missing_marks_a_required_field():
    schema = dataclasses.make_dataclass("Schema", [("value", int, MISSING)])
    assert read_fields(schema)["value"].is_required
