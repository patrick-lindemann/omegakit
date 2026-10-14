import dataclasses
import functools
import itertools
import types
from collections.abc import Callable
from typing import Any, TypeAliasType, Union, get_args, get_origin, is_typeddict

from omegaconf import OmegaConf
from omegaconf.errors import OmegaConfBaseException


def split_union(annotation: Any) -> tuple[Any, ...]:
    while isinstance(annotation, TypeAliasType):
        annotation = annotation.__value__
    if get_origin(annotation) not in (Union, types.UnionType):
        return (annotation,)
    members = [split_union(member) for member in get_args(annotation)]
    return tuple(itertools.chain.from_iterable(members))


def find_section(annotation: Any) -> type | None:
    for member in split_union(annotation):
        if is_typeddict(member):
            return member
    return None


def find_item_annotation(
    annotation: Any, containers: tuple[type, ...] = (list, dict)
) -> Any:
    members = [
        member for member in split_union(annotation) if member is not types.NoneType
    ]
    if len(members) != 1 or (get_origin(members[0]) or members[0]) not in containers:
        return None
    item_annotations = get_args(members[0])
    return item_annotations[-1] if item_annotations else Any


def find_key_annotation(annotation: Any) -> Any:
    members = [
        member for member in split_union(annotation) if member is not types.NoneType
    ]
    if len(members) != 1 or get_origin(members[0]) is not dict:
        return Any
    return get_args(members[0])[0]


def find_tuple_annotations(annotation: Any, length: int) -> list[Any] | None:
    members = [
        member for member in split_union(annotation) if member is not types.NoneType
    ]
    if len(members) != 1 or (get_origin(members[0]) or members[0]) is not tuple:
        return None
    item_annotations = get_args(members[0])
    if not item_annotations:
        return [Any] * length
    if item_annotations[-1] is Ellipsis:
        return [item_annotations[0]] * length
    return list(item_annotations)


def is_data(annotation: Any) -> bool:
    try:
        return _is_data_cached(annotation)
    # An annotation that cannot be hashed, such as `Literal[[1, 2]]`, is probed anew
    except TypeError:
        return _is_data_cached.__wrapped__(annotation)


def is_object(annotation: Any) -> bool:
    for member in split_union(annotation):
        item_annotation = find_item_annotation(member)
        if item_annotation is not None:
            if not is_object(item_annotation):
                return False
            continue
        tuple_annotations = find_tuple_annotations(member, 1)
        if tuple_annotations is not None:
            if not all(is_object(item) for item in tuple_annotations):
                return False
            continue
        cls = get_origin(member) or member
        if (
            not isinstance(cls, type)
            or cls in (set, frozenset)
            or (cls.__module__ == "collections.abc" and cls is not Callable)
        ):
            return False
    return True


@functools.cache
def _is_data_cached(annotation: Any) -> bool:
    # A dataclass is an object, although OmegaConf reads it as a structured config
    is_object = any(
        is_typeddict(member) or dataclasses.is_dataclass(member)
        for member in split_union(annotation)
    )
    if annotation is Any or is_object:
        return False
    item_annotation = find_item_annotation(annotation)
    if item_annotation is not None and not is_data(item_annotation):
        return False
    tuple_annotations = find_tuple_annotations(annotation, 1)
    if tuple_annotations is not None and not all(
        is_data(item) for item in tuple_annotations
    ):
        return False
    probe = dataclasses.make_dataclass("Probe", [("value", annotation)])
    try:
        OmegaConf.structured(probe)
    # OmegaConf asserts that the type of a key is a class
    except (OmegaConfBaseException, AssertionError):
        return False
    return True
