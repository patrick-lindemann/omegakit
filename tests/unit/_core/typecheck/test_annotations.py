import sys
import typing
from typing import Any, Literal, TypedDict, TypeVar

import pytest
import typing_extensions

from omegakit._core.typecheck.annotations import (
    find_item_annotation,
    find_key_annotation,
    find_position_annotations,
    find_typed_dict,
    resolve_aliases,
    union_members,
)

T = TypeVar("T")


class _Section(TypedDict):
    width: int


_BackportedAlias = typing_extensions.TypeAliasType("_BackportedAlias", int | str | None)
_Size = typing_extensions.TypeAliasType("_Size", int)
_Pair = typing_extensions.TypeAliasType("_Pair", tuple[T, T], type_params=(T,))
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


def test_alias_with_arguments_is_one_member():
    assert union_members(_Pair[int]) == (_Pair[int],)


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
        (list[int] | dict[str, int], None),
    ],
)
def test_item_annotation_is_found_in_one_container(
    annotation: Any, item_annotation: Any
):
    assert find_item_annotation(annotation) == item_annotation


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


def test_section_is_the_typed_dict_of_a_union():
    assert find_typed_dict(_Section | None) is _Section
    assert find_typed_dict(int) is None
