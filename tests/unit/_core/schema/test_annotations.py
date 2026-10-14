from typing import Any, TypedDict

import pytest

from omegakit._core.schema.annotations import (
    find_item_annotation,
    find_key_annotation,
    find_position_annotations,
    find_typed_dict,
    union_members,
)


class _Section(TypedDict):
    width: int


type _Alias = int | str | None


def test_union_is_split_into_its_members():
    assert union_members(int | str) == (int, str)
    assert union_members(_Alias) == (int, str, type(None))
    assert union_members(int) == (int,)


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
