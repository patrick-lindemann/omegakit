import sys
import typing
from typing import Annotated, Any, Literal, TypedDict, TypeVar

import pytest
import typing_extensions

from omegakit._core.errors import SchemaDefinitionError
from omegakit._core.typecheck.annotations import (
    find_item_annotation,
    find_key_annotation,
    find_position_annotations,
    find_typed_dicts,
    is_instance,
    resolve_aliases,
    union_members,
)

T = TypeVar("T")


class _Section(TypedDict):
    width: int


class _OtherSection(TypedDict):
    depth: int


_BackportedAlias = typing_extensions.TypeAliasType("_BackportedAlias", int | str | None)
_Size = typing_extensions.TypeAliasType("_Size", int)
_Pair = typing_extensions.TypeAliasType("_Pair", tuple[T, T], type_params=(T,))
_Optional = typing_extensions.TypeAliasType("_Optional", T | None, type_params=(T,))
_Tree = typing_extensions.TypeAliasType("_Tree", int | list["_Tree"])
_Wrapped = typing_extensions.TypeAliasType("_Wrapped", Annotated[_Section, "doc"] | int)
_ALIASES: dict[str, Any] = {"typing_extensions": _BackportedAlias}
if sys.version_info >= (3, 12):
    # The class of an alias that a `type` statement makes
    _Alias = typing.TypeAliasType("_Alias", int | str | None)
    _ALIASES["typing"] = _Alias


def test_union_is_split_into_its_members():
    assert union_members(int | str) == (int, str)
    assert union_members(int) == (int,)


@pytest.mark.parametrize("alias", _ALIASES.values(), ids=_ALIASES.keys())
def test_alias_is_split_into_the_members_of_its_value(alias: Any):
    assert union_members(alias) == (int, str, type(None))


def test_alias_with_arguments_is_split_into_the_members_of_its_value():
    assert union_members(_Pair[int]) == (tuple[int, int],)
    assert union_members(_Optional[_Section]) == (_Section, type(None))


@pytest.mark.parametrize(
    "annotation",
    [
        Annotated[_Section | int, "doc"],
        Annotated[_Section, "doc"] | int,
        _Wrapped,
        typing_extensions.Required[_Section | int],
        typing_extensions.NotRequired[_Section | int],
        typing_extensions.ReadOnly[_Section | int],
    ],
)
def test_qualifier_is_not_a_member(annotation: Any):
    assert union_members(annotation) == (_Section, int)


def test_recursive_alias_is_unwrapped_once():
    assert union_members(_Tree) == (int, list["_Tree"])


@pytest.mark.parametrize(
    ("annotation", "resolved"),
    [
        (_Size, int),
        (list[_Size], list[int]),
        (dict[str, _Size] | None, dict[str, int] | None),
        (_Size | None, int | None),
        (_Pair[int], tuple[int, int]),
        (list[_Pair[_Size]], list[tuple[int, int]]),
        (Literal["a", "b"], Literal["a", "b"]),
    ],
)
def test_alias_of_typing_extensions_is_resolved_into_its_value(
    annotation: Any, resolved: Any
):
    assert resolve_aliases(annotation) == resolved


@pytest.mark.skipif(sys.version_info < (3, 12), reason="needs a `type` statement")
def test_alias_of_a_type_statement_is_left_to_omegaconf():
    alias = _ALIASES["typing"]
    assert resolve_aliases(list[alias]) == list[alias]


@pytest.mark.parametrize(
    ("annotation", "item_annotation"),
    [
        (list[int], int),
        (list[int] | None, int),
        (dict[str, float], float),
        (list, Any),
        (int, None),
        (list[_Section] | int, _Section),
        (list[_Section] | _Section, _Section),
        (_Optional[list[_Section]], _Section),
    ],
)
def test_item_annotation_is_found_in_one_container(
    annotation: Any, item_annotation: Any
):
    assert find_item_annotation(annotation) == item_annotation


def test_kind_of_the_node_names_the_container_of_a_union():
    annotation = list[int] | dict[str, float]
    assert find_item_annotation(annotation, (list,)) is int
    assert find_item_annotation(annotation, (dict,)) is float


@pytest.mark.parametrize(
    "annotation", [list[_Section] | list[int], dict[str, int] | dict[str, _Section]]
)
def test_several_containers_of_one_kind_are_rejected(annotation: Any):
    with pytest.raises(SchemaDefinitionError, match="holds several"):
        find_item_annotation(annotation, (list, dict))


@pytest.mark.parametrize(
    ("annotation", "key_annotation"),
    [
        (dict[int, str], int),
        (dict[int, str] | None, int),
        (dict, Any),
        (list[int], None),
    ],
)
def test_key_annotation_is_found_in_a_dictionary(annotation: Any, key_annotation: Any):
    assert find_key_annotation(annotation) == key_annotation


@pytest.mark.parametrize(
    ("annotation", "item_annotations"),
    [
        (tuple[int, str], [int, str]),
        (tuple[int, ...], [int, int, int]),
        (tuple, [Any, Any, Any]),
        (tuple[int, str] | None, [int, str]),
        (list[int], None),
    ],
)
def test_annotations_of_the_positions_of_a_tuple_are_found(
    annotation: Any, item_annotations: list[Any] | None
):
    assert find_position_annotations(annotation, 3) == item_annotations


class _Base:
    pass


class _Derived(_Base):
    pass


class _Named(typing.Protocol):
    name: str


@pytest.mark.parametrize(
    ("value", "annotation", "expected"),
    [
        (_Derived, type[_Base], True),
        (int, type[_Base], False),
        (int, type[_Base] | type, True),
        (int, type[_Base] | typing.Type, True),  # noqa: UP006
        (int, type[_Base] | type[Any], True),
        (int, type[_Base | int], True),
        (int, type[typing.Union[_Base, int]], True),  # noqa: UP007
        (int, type[_Base] | int, False),
        (_Derived(), _Base, True),
        (5, _Base | str, False),
        (5, Any, True),
        (5, _Named | str, True),
        (5, Literal[1], True),
        ({}, _Section, False),
        ([1], list[str] | None, True),
    ],
)
def test_value_is_checked_by_each_member_of_a_union(
    value: Any, annotation: Any, expected: bool
):
    assert is_instance(value, annotation) is expected


def test_sections_are_the_typed_dicts_of_a_union():
    assert find_typed_dicts(_Section | None) == (_Section,)
    assert find_typed_dicts(_Section | int | _OtherSection) == (_Section, _OtherSection)
    assert find_typed_dicts(int) == ()
