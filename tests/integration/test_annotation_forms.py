"""Every spelling of an annotation is checked as the type that it stands for.

The schemas are declared under `from __future__ import annotations`, with
`typing.TypedDict` and with `typing_extensions.TypedDict`. Each is reached through
every form and container below, given in the config or through `$symbol`, and
checked by `validate` and `instantiate`.
"""

from __future__ import annotations

import sys
import typing
from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated, Any, Literal, TypedDict, TypeVar

import pytest
import typing_extensions
from omegaconf import OmegaConf
from typing_extensions import NotRequired, TypeAliasType

from omegakit._core.configurable import Configurable
from omegakit._core.errors import ConfigSchemaError
from omegakit._core.instantiate import instantiate
from omegakit._core.schema import validate

T = TypeVar("T")


class Point(TypedDict):
    x: int
    y: int


class Square(TypedDict):
    kind: Literal["square"]
    side: int
    label: NotRequired[Annotated[str, "doc"]]


class Circle(TypedDict):
    kind: Literal["circle"]
    radius: int
    center: NotRequired[Point]


class BackportedPoint(typing_extensions.TypedDict):
    x: int
    y: int


class BackportedSquare(typing_extensions.TypedDict):
    kind: Literal["square"]
    side: int
    label: NotRequired[Annotated[str, "doc"]]


class BackportedCircle(typing_extensions.TypedDict):
    kind: Literal["circle"]
    radius: int
    center: NotRequired[BackportedPoint]


@dataclass(frozen=True)
class _Container:
    make_annotation: Callable[[Any], Any]
    wrap: Callable[[Any], Any]
    unwrap: Callable[[Any], Any]
    key: str


Optional = TypeAliasType("Optional", T | None, type_params=(T,))
Documented = TypeAliasType("Documented", Annotated[T, "doc"], type_params=(T,))
_FORMS: dict[str, Callable[[Any], Any]] = {
    "plain": lambda member: member,
    "optional": lambda member: member | None,
    "alias": lambda member: Optional[member],
    "annotated": lambda member: Annotated[member, "doc"],
    "annotated-alias": lambda member: Documented[member],
}
if sys.version_info >= (3, 12):
    # The class of an alias that a `type` statement makes
    StatementOptional = typing.TypeAliasType(
        "StatementOptional", T | None, type_params=(T,)
    )
    _FORMS["statement-alias"] = lambda member: StatementOptional[member]
_CONTAINERS = {
    "mapping": _Container(lambda form: form, lambda shape: shape, lambda v: v, ""),
    "list": _Container(lambda form: list[form], lambda s: [s], lambda v: v[0], "[0]"),
    "dict": _Container(
        lambda form: dict[str, form], lambda s: {"k": s}, lambda v: v["k"], ".k"
    ),
    "tuple": _Container(
        lambda form: tuple[form, ...], lambda s: [s], lambda v: v[0], "[0]"
    ),
    "pair": _Container(
        lambda form: tuple[form, int], lambda s: [s, 1], lambda v: v[0], "[0]"
    ),
    "list-or-int": _Container(
        lambda form: list[form] | int, lambda s: [s], lambda v: v[0], "[0]"
    ),
}
_SCHEMAS = {
    "typing": (Square, Circle),
    "typing_extensions": (BackportedSquare, BackportedCircle),
}
_MEMBERS: dict[str, Callable[[type, type], Any]] = {
    "single": lambda square, circle: square,
    "union": lambda square, circle: square | circle,
}
_SQUARE = {"kind": "square", "side": "2"}
_WRONG_SHAPES = {
    "unknown-key": ({"kind": "square", "side": 2, "typo": 1}, ""),
    "missing-key": ({"kind": "square", "label": "a"}, ""),
    "wrong-value": ({"kind": "square", "side": "wide"}, ".side"),
}
_WRONG_CIRCLE = {"kind": "circle", "radius": 1, "center": {"x": 1, "z": 2}}
# What a `$symbol` names, set by each test
VALUE: Any = None


class Holder(Configurable):
    def __init__(self, **config: Any):
        self.config = config


def _make_annotation(schemas: str, member: str, form: str, container: str) -> Any:
    square, circle = _SCHEMAS[schemas]
    return _CONTAINERS[container].make_annotation(
        _FORMS[form](_MEMBERS[member](square, circle))
    )


def _make_config(
    monkeypatch: pytest.MonkeyPatch, annotation: Any, value: Any, given: str
) -> Any:
    # A new class per annotation, which `$target` reaches through this module
    schema = TypedDict("schema", {"value": annotation})  # noqa: UP013
    target = type("Target", (Holder,), {"schema": schema})
    monkeypatch.setattr(sys.modules[__name__], "TARGET", target, raising=False)
    if given == "symbol":
        monkeypatch.setattr(sys.modules[__name__], "VALUE", value)
        value = {"$symbol": f"{__name__}.VALUE"}
    return OmegaConf.create({"$target": f"{__name__}.TARGET", "value": value})


_CASES = pytest.mark.parametrize(
    ("schemas", "member", "form", "container"),
    [
        (schemas, member, form, container)
        for schemas in _SCHEMAS
        for member in _MEMBERS
        for form in _FORMS
        for container in _CONTAINERS
    ],
)
_UNION_CASES = pytest.mark.parametrize(
    ("schemas", "form", "container"),
    [
        (schemas, form, container)
        for schemas in _SCHEMAS
        for form in _FORMS
        for container in _CONTAINERS
    ],
)
_GIVEN = pytest.mark.parametrize("given", ["config", "symbol"])


@_GIVEN
@_CASES
def test_valid_value_is_checked_and_converted(
    monkeypatch: pytest.MonkeyPatch,
    schemas: str,
    member: str,
    form: str,
    container: str,
    given: str,
):
    annotation = _make_annotation(schemas, member, form, container)
    value = _CONTAINERS[container].wrap(_SQUARE)
    config = _make_config(monkeypatch, annotation, value, given)
    validate(config)
    result = instantiate(config)
    assert _CONTAINERS[container].unwrap(result.config["value"]) == {
        "kind": "square",
        "side": 2,
    }


@pytest.mark.parametrize("wrong_shape", _WRONG_SHAPES)
@_GIVEN
@_CASES
def test_wrong_value_is_rejected_at_its_place(
    monkeypatch: pytest.MonkeyPatch,
    schemas: str,
    member: str,
    form: str,
    container: str,
    given: str,
    wrong_shape: str,
):
    annotation = _make_annotation(schemas, member, form, container)
    shape, shape_key = _WRONG_SHAPES[wrong_shape]
    value = _CONTAINERS[container].wrap(shape)
    config = _make_config(monkeypatch, annotation, value, given)
    # A value behind `$symbol` is no part of the config, and its keys name nothing
    key = (
        "value"
        if given == "symbol"
        else f"value{_CONTAINERS[container].key}{shape_key}"
    )
    with pytest.raises(ConfigSchemaError) as error_info:
        validate(config)
    assert error_info.value.full_key == key


@_GIVEN
@_UNION_CASES
def test_wrong_value_in_a_nested_schema_is_rejected(
    monkeypatch: pytest.MonkeyPatch, schemas: str, form: str, container: str, given: str
):
    annotation = _make_annotation(schemas, "union", form, container)
    value = _CONTAINERS[container].wrap(_WRONG_CIRCLE)
    config = _make_config(monkeypatch, annotation, value, given)
    key = "value" if given == "symbol" else f"value{_CONTAINERS[container].key}.center"
    with pytest.raises(ConfigSchemaError, match="`z` is not a field") as error_info:
        validate(config)
    assert error_info.value.full_key == key
