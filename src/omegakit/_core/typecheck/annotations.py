import dataclasses
import functools
import itertools
import operator
import sys
import types
import typing
from collections.abc import Callable
from typing import Any, Literal, TypeVar, Union, get_args, get_origin

import typing_extensions
from omegaconf import OmegaConf
from omegaconf.errors import OmegaConfBaseException
from typing_extensions import is_typeddict

if sys.version_info >= (3, 12):
    # A `type` statement makes a `typing.TypeAliasType`, which OmegaConf resolves, and
    # which can be another class than that of `typing_extensions`
    _OMEGACONF_ALIAS_TYPES = (typing.TypeAliasType,)
else:
    _OMEGACONF_ALIAS_TYPES = ()
_TYPE_ALIAS_TYPES = (*_OMEGACONF_ALIAS_TYPES, typing_extensions.TypeAliasType)


def union_members(annotation: Any) -> tuple[Any, ...]:
    while _is_bare_alias(annotation, _TYPE_ALIAS_TYPES):
        annotation = annotation.__value__
    if get_origin(annotation) not in (Union, types.UnionType):
        return (annotation,)
    members = [union_members(member) for member in get_args(annotation)]
    return tuple(itertools.chain.from_iterable(members))


def resolve_aliases(annotation: Any) -> Any:
    if _is_alias_unknown_to_omegaconf(annotation):
        return resolve_aliases(annotation.__value__)
    origin = get_origin(annotation)
    if _is_alias_unknown_to_omegaconf(origin):
        value = _substitute_type_parameters(annotation)
        return annotation if value is annotation else resolve_aliases(value)
    arguments = get_args(annotation)
    if origin is None or origin is Literal or not arguments:
        return annotation
    resolved_arguments = tuple(resolve_aliases(argument) for argument in arguments)
    pairs = zip(resolved_arguments, arguments, strict=True)
    if all(resolved is argument for resolved, argument in pairs):
        return annotation
    try:
        if origin is types.UnionType:
            return functools.reduce(operator.or_, resolved_arguments)
        return origin[resolved_arguments]
    # Not every annotation can be made again of new arguments
    except TypeError:
        return annotation


def find_typed_dict(annotation: Any) -> type | None:
    for member in union_members(annotation):
        if is_typeddict(member):
            return member
    return None


def find_item_annotation(
    annotation: Any, containers: tuple[type, ...] = (list, dict)
) -> Any:
    member = _find_single_container(annotation, containers)
    if member is None:
        return None
    item_annotations = get_args(member)
    return item_annotations[-1] if item_annotations else Any


def find_key_annotation(annotation: Any) -> Any:
    member = _find_single_container(annotation, (dict,))
    if member is None:
        return None
    key_annotations = get_args(member)
    return key_annotations[0] if key_annotations else Any


def find_position_annotations(annotation: Any, length: int) -> list[Any] | None:
    member = _find_single_container(annotation, (tuple,))
    if member is None:
        return None
    item_annotations = get_args(member)
    if not item_annotations:
        return [Any] * length
    if item_annotations[-1] is Ellipsis:
        return [item_annotations[0]] * length
    return list(item_annotations)


def is_plain_value(annotation: Any) -> bool:
    try:
        return _is_plain_value_cached(annotation)
    # An annotation that cannot be hashed, such as `Literal[[1, 2]]`, is probed anew
    except TypeError:
        return _is_plain_value_cached.__wrapped__(annotation)


def holds_objects(annotation: Any) -> bool:
    for member in union_members(annotation):
        item_annotation = find_item_annotation(member)
        if item_annotation is not None:
            if not holds_objects(item_annotation):
                return False
            continue
        position_annotations = find_position_annotations(member, 1)
        if position_annotations is not None:
            if not all(holds_objects(item) for item in position_annotations):
                return False
            continue
        cls = get_origin(member) or member
        # `Any` is a class only from Python 3.11 on
        if cls is not Any and (
            not isinstance(cls, type)
            or cls in (set, frozenset)
            or (cls.__module__ == "collections.abc" and cls is not Callable)
        ):
            return False
    return True


@functools.cache
def _is_plain_value_cached(annotation: Any) -> bool:
    # A dataclass is an object, although OmegaConf reads it as a structured config
    is_built = any(
        is_typeddict(member) or dataclasses.is_dataclass(member)
        for member in union_members(annotation)
    )
    if annotation is Any or is_built:
        return False
    item_annotation = find_item_annotation(annotation)
    if item_annotation is not None and not is_plain_value(item_annotation):
        return False
    position_annotations = find_position_annotations(annotation, 1)
    if position_annotations is not None and not all(
        is_plain_value(item) for item in position_annotations
    ):
        return False
    probe = dataclasses.make_dataclass(
        "Probe", [("value", resolve_aliases(annotation))]
    )
    try:
        OmegaConf.structured(probe)
    # OmegaConf asserts that the type of a key is a class
    except (OmegaConfBaseException, AssertionError):
        return False
    return True


def _find_single_container(annotation: Any, containers: tuple[type, ...]) -> Any:
    members = [
        member for member in union_members(annotation) if member is not types.NoneType
    ]
    if len(members) != 1 or (get_origin(members[0]) or members[0]) not in containers:
        return None
    return members[0]


def _is_alias_unknown_to_omegaconf(annotation: Any) -> bool:
    return _is_bare_alias(
        annotation, (typing_extensions.TypeAliasType,)
    ) and not isinstance(annotation, _OMEGACONF_ALIAS_TYPES)


def _is_bare_alias(annotation: Any, alias_types: tuple[type, ...]) -> bool:
    # On Python 3.10, an alias with arguments passes for an instance of its class
    return isinstance(annotation, alias_types) and get_origin(annotation) is None


def _substitute_type_parameters(annotation: Any) -> Any:
    alias = get_origin(annotation)
    arguments = get_args(annotation)
    parameters = alias.__type_params__
    # A `TypeVarTuple`, a `ParamSpec` or a default needs more than a substitution
    if len(arguments) != len(parameters) or not all(
        isinstance(parameter, TypeVar) for parameter in parameters
    ):
        return annotation
    value = alias.__value__
    value_parameters = getattr(value, "__parameters__", ())
    if not value_parameters:
        return value
    substitutions = dict(zip(parameters, arguments, strict=True))
    try:
        return value[tuple(substitutions[parameter] for parameter in value_parameters)]
    # The value has a parameter that the alias does not declare, or takes none
    except (KeyError, TypeError):
        return annotation
