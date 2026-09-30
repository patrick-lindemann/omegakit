import collections.abc
import dataclasses
import types
from typing import Any, TypeAliasType, Union, get_args, get_origin, is_typeddict


def split_union(annotation: Any) -> tuple[tuple[Any, ...], bool]:
    """Split an annotation into its members, following type aliases.

    Args:
        annotation: The annotation, possibly a union or a `type` alias.

    Returns:
        The members of a union other than `None`, or the annotation alone, and
        whether the union contains `None`.
    """
    while isinstance(annotation, TypeAliasType):
        annotation = annotation.__value__
    if get_origin(annotation) not in (Union, types.UnionType):
        return (annotation,), False
    members = tuple(
        member for member in get_args(annotation) if member is not type(None)
    )
    return members, len(members) < len(get_args(annotation))


def find_section(annotation: Any) -> type | None:
    """Find the dataclass in an object field's annotation, if there is one.

    Args:
        annotation: The field's annotation, possibly a union or a `type` alias.

    Returns:
        The first dataclass among the annotation's members, or `None`.
    """
    members, _ = split_union(annotation)
    for member in members:
        if isinstance(member, type) and dataclasses.is_dataclass(member):
            return member
    return None


def is_mapping_type(annotation: Any) -> bool:
    """Tell whether an annotation describes a mapping.

    Args:
        annotation: The annotation.

    Returns:
        `True` for a `dict`, a `Mapping`, a dataclass or a `TypedDict`.
    """
    origin = get_origin(annotation) or annotation
    return origin in (dict, collections.abc.Mapping) or (
        isinstance(annotation, type)
        and (dataclasses.is_dataclass(annotation) or is_typeddict(annotation))
    )


def is_sequence_type(annotation: Any) -> bool:
    """Tell whether an annotation describes a sequence.

    Args:
        annotation: The annotation.

    Returns:
        `True` for a `list`, a `tuple` or a `Sequence`.
    """
    origin = get_origin(annotation) or annotation
    return origin in (list, tuple, collections.abc.Sequence)
