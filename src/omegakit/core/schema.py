import collections.abc
import copy
import dataclasses
import enum
import functools
import inspect
import operator
import sys
import types
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import (
    Any,
    Literal,
    TypeAliasType,
    TypeVar,
    Union,
    get_args,
    get_origin,
    get_type_hints,
    is_typeddict,
)

from omegaconf import MISSING, OmegaConf
from omegaconf.errors import OmegaConfBaseException
from typing_extensions import NoDefault

from .configurable import Configurable
from .errors import OmegaKitBaseException, SchemaDefinitionError
from .utils import describe_error

type FieldKind = Literal["data", "object", "any"]

_SCALAR_TYPES = (int, float, bool, str, bytes, Path)
_UNSUPPORTED_CONTAINERS = (
    set,
    frozenset,
    collections.abc.Iterable,
    collections.abc.Collection,
    collections.abc.MutableSequence,
    collections.abc.Set,
    collections.abc.MutableSet,
    collections.abc.MutableMapping,
)


@functools.cache
def find_schema(cls: type) -> type | None:
    """Find the schema of a class. A schema is a plain dataclass.

    Args:
        cls: The class to inspect.

    Returns:
        `cls` itself if it is a dataclass, the `TConfig` of a `Configurable` if
        that is a dataclass, and otherwise `None`.

    Raises:
        SchemaDefinitionError: If the schema uses a dataclass feature outside the
            supported subset, or a type variable in the bases of `cls` cannot be
            resolved.
    """  # noqa: DOC503
    if issubclass(cls, Configurable):
        parameters = getattr(cls, "__parameters__", ())
        config_type = _find_config_type(
            cls, {parameter: _type_var_default(parameter) for parameter in parameters}
        )
    else:
        config_type = cls
    if not (isinstance(config_type, type) and dataclasses.is_dataclass(config_type)):
        return None
    try:
        OmegaConf.structured(derive_structure(config_type))
    except OmegaKitBaseException:
        raise
    except OmegaConfBaseException as error:
        owner = "" if config_type is cls else f" of `{cls.__qualname__}`"
        raise SchemaDefinitionError(
            f"Schema `{config_type.__qualname__}`{owner} cannot be validated by "
            f"OmegaConf: {describe_error(error)}"
        ) from error
    return config_type


@functools.cache
def classify_fields(
    schema: type, outer: tuple[type, ...] = ()
) -> Mapping[str, tuple[FieldKind, Any]]:
    """Classify the configurable fields of a schema.

    Args:
        schema: The schema, a dataclass.
        outer: The dataclasses whose fields lead to `schema`, outermost first.
            Defaults to `()`.

    Returns:
        The kind and resolved annotation of every configurable field, by field name,
        read-only because the result is cached.

    Raises:
        SchemaDefinitionError: If the schema uses a dataclass feature outside the
            supported subset, or contains itself.
    """
    if schema in outer:
        cycle = (*outer[outer.index(schema) :], schema)
        raise SchemaDefinitionError(
            f"Schema `{schema.__qualname__}` contains itself: "
            f"{' -> '.join(cls.__qualname__ for cls in cycle)}. Recursive schemas are "
            "not supported."
        )
    hints = _type_hints(schema)
    for name, hint in hints.items():
        if isinstance(hint, dataclasses.InitVar) and not hasattr(schema, name):
            raise SchemaDefinitionError(
                f"Field `{name}` of schema `{schema.__qualname__}` is an `InitVar` "
                "without a default, which a config cannot set. Give it a default."
            )
    return types.MappingProxyType(
        {
            field.name: (
                _field_kind(hints[field.name], schema, field.name, (*outer, schema)),
                hints[field.name],
            )
            for field in dataclasses.fields(schema)
            if field.init
        }
    )


@functools.cache
def check_schema(cls: type) -> None:
    """Check that the schema of `cls` matches its `__init__`.

    Args:
        cls: The class to check.

    Raises:
        SchemaDefinitionError: If the schema is not supported, a required parameter
            has no field, a field has no parameter and `__init__` takes no
            `**kwargs`, or a field's annotation is not assignable to its
            parameter's annotation.
        TypeError: If `cls` is not a class.
    """  # noqa: DOC503
    schema = find_schema(cls)
    if (
        schema is None
        or schema is cls
        or any(
            "from_config" in vars(base)
            for base in cls.__mro__
            if base is not Configurable
        )
    ):
        return
    fields = classify_fields(schema)
    parameters = inspect.signature(cls).parameters
    hints = _init_hints(cls)
    keyword_names = {
        name
        for name, parameter in parameters.items()
        if parameter.kind
        in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
    }
    takes_kwargs = any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD
        for parameter in parameters.values()
    )
    for name, parameter in parameters.items():
        if (
            parameter.default is inspect.Parameter.empty
            and parameter.kind
            not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
            and name not in fields
        ):
            raise SchemaDefinitionError(
                f"Schema `{schema.__qualname__}` of `{cls.__qualname__}` has no field "
                f"for the required parameter `{name}`."
            )
    for name, (_, annotation) in fields.items():
        if name not in keyword_names:
            positional = name in parameters and (
                parameters[name].kind is inspect.Parameter.POSITIONAL_ONLY
            )
            if takes_kwargs and not positional:
                continue
            reason = (
                "takes it only positionally" if positional else "takes no `**kwargs`"
            )
            raise SchemaDefinitionError(
                f"Field `{name}` of schema `{schema.__qualname__}` is not a keyword "
                f"parameter of `{cls.__qualname__}`, and `__init__` {reason}."
            )
        if name in hints and not _is_assignable(annotation, hints[name]):
            raise SchemaDefinitionError(
                f"Field `{name}` of schema `{schema.__qualname__}` has `{annotation}`, "
                f"which is not assignable to `{hints[name]}` in "
                f"`{cls.__qualname__}.__init__`."
            )


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


# OmegaConf 2.3 supports neither `Literal`, nor unions with non-scalar members, nor
# fixed-length tuples, so it validates against a derived structure that holds plain
# types there. The rest is checked after OmegaConf, and building constructs the
# schema's own classes, so every supported OmegaConf version behaves the same.
@functools.cache
def derive_structure(schema: type) -> type:
    """Derive the dataclass that OmegaConf validates the data fields of a schema with.

    Args:
        schema: The schema, a dataclass.

    Returns:
        A dataclass with the data fields of `schema`, whose annotations OmegaConf
        supports.
    """
    fields = classify_fields(schema)
    structure = []
    for field in dataclasses.fields(schema):
        if field.name not in fields or fields[field.name][0] != "data":
            continue
        field_type = derive_structure_type(fields[field.name][1])
        if field.default_factory is not dataclasses.MISSING:
            default = dataclasses.field(
                default_factory=functools.partial(
                    _structure_default, field.default_factory, field_type is Any
                )
            )
        elif field.default is not dataclasses.MISSING:
            default = dataclasses.field(
                default_factory=functools.partial(
                    _structure_default,
                    functools.partial(copy.deepcopy, field.default),
                    field_type is Any,
                )
            )
        else:
            default = dataclasses.field(default=MISSING)
        structure.append((field.name, field_type, default))
    return dataclasses.make_dataclass(schema.__name__, structure, kw_only=True)


def derive_structure_type(annotation: Any) -> Any:
    """Translate an annotation into one that OmegaConf supports.

    Args:
        annotation: The annotation of a data field.

    Returns:
        The annotation with `Literal`, unions with non-scalar members and fixed-length
        tuples replaced by plain types, and dataclasses by their derived structure.
    """
    while isinstance(annotation, TypeAliasType):
        annotation = annotation.__value__
    if annotation is collections.abc.Sequence:
        return list
    if annotation is collections.abc.Mapping:
        return dict
    origin = get_origin(annotation)
    arguments = get_args(annotation)
    if origin is Literal:
        return functools.reduce(
            operator.or_, dict.fromkeys(type(value) for value in arguments)
        )
    if origin in (Union, types.UnionType):
        members, _ = split_union(annotation)
        if len(members) == 1:
            return derive_structure_type(members[0]) | None
        if any(
            is_mapping_type(member) or is_sequence_type(member) for member in arguments
        ):
            return Any
        return functools.reduce(operator.or_, map(derive_structure_type, arguments))
    if origin in (list, collections.abc.Sequence) or (
        origin is tuple and len(arguments) == 2 and arguments[1] is Ellipsis
    ):
        return list[derive_structure_type(arguments[0])]
    if origin is tuple:
        return Any
    if origin in (dict, collections.abc.Mapping):
        return dict[arguments[0], derive_structure_type(arguments[1])]
    if isinstance(annotation, type) and is_typeddict(annotation):
        return dict
    if isinstance(annotation, type) and dataclasses.is_dataclass(annotation):
        return derive_structure(annotation)
    return annotation


def _type_var_default(parameter: Any) -> Any:
    return getattr(parameter, "__default__", NoDefault)


def _find_config_type(cls: type, substitutions: dict[Any, Any]) -> Any:
    for base in types.get_original_bases(cls):
        origin = get_origin(base) or base
        if not (isinstance(origin, type) and issubclass(origin, Configurable)):
            continue
        arguments = tuple(
            _substitute(argument, substitutions, cls) for argument in get_args(base)
        )
        parameters = getattr(origin, "__parameters__", ())
        if not arguments:
            arguments = tuple(_type_var_default(parameter) for parameter in parameters)
        if origin is Configurable:
            return arguments[0]
        return _find_config_type(origin, dict(zip(parameters, arguments, strict=True)))
    return NoDefault


def _substitute(argument: Any, substitutions: dict[Any, Any], cls: type) -> Any:
    if not isinstance(argument, TypeVar):
        return argument
    if argument not in substitutions:
        raise SchemaDefinitionError(
            f"Cannot resolve type variable `{argument}` in the bases of "
            f"`{cls.__qualname__}`."
        )
    return substitutions[argument]


def _type_hints(schema: type) -> dict[str, Any]:
    try:
        return get_type_hints(schema)
    except NameError as error:
        for field in dataclasses.fields(schema):
            if not isinstance(field.type, str):
                continue
            # An inherited field shares its `Field` with the base that defines it.
            owner = next(
                base
                for base in reversed(schema.__mro__)
                if getattr(base, "__dataclass_fields__", {}).get(field.name) is field
            )
            try:
                eval(
                    field.type,
                    vars(sys.modules[owner.__module__]),
                    dict(vars(owner)),
                )
            except NameError:
                raise SchemaDefinitionError(
                    f"Cannot resolve the annotation of field `{field.name}` of schema "
                    f"`{schema.__qualname__}`: {error}. Import the type at module "
                    "level, not under `TYPE_CHECKING` or inside a function."
                ) from error
        raise SchemaDefinitionError(
            f"Cannot resolve the annotations of schema `{schema.__qualname__}`: "
            f"{error}."
        ) from error
    # Evaluating an annotation runs arbitrary code, which can raise anything.
    except Exception as error:
        raise SchemaDefinitionError(
            f"Cannot resolve the annotations of schema `{schema.__qualname__}`: "
            f"{describe_error(error)}."
        ) from error


def _init_hints(cls: type) -> dict[str, Any]:
    try:
        return get_type_hints(cls.__init__)
    except Exception:
        # Annotations imported under `TYPE_CHECKING` do not resolve; check the rest.
        hints = {}
        for name, annotation in getattr(cls.__init__, "__annotations__", {}).items():
            try:
                hints[name] = (
                    eval(annotation, vars(sys.modules[cls.__init__.__module__]))
                    if isinstance(annotation, str)
                    else annotation
                )
            except Exception:
                continue
        return hints


def _field_kind(
    annotation: Any, schema: type, name: str, outer: tuple[type, ...]
) -> FieldKind:
    while isinstance(annotation, TypeAliasType):
        annotation = annotation.__value__
    origin = get_origin(annotation)
    arguments = get_args(annotation)
    if origin is Literal:
        if all(type(value) in (str, int, bool) for value in arguments):
            return "data"
        raise SchemaDefinitionError(
            f"Field `{name}` of schema `{schema.__qualname__}` has `{annotation}`, but "
            "`Literal` values must be strings, integers or booleans."
        )
    if annotation is Any:
        return "any"
    if annotation in _SCALAR_TYPES or (
        isinstance(annotation, type) and issubclass(annotation, enum.Enum)
    ):
        return "data"
    if isinstance(annotation, type) and dataclasses.is_dataclass(annotation):
        kinds = {kind for kind, _ in classify_fields(annotation, outer).values()}
        return "data" if kinds <= {"data"} else "object"
    if isinstance(annotation, type) and is_typeddict(annotation):
        return "data"
    if origin in (Union, types.UnionType):
        members, _ = split_union(annotation)
        member_kinds: set[FieldKind] = {
            _field_kind(member, schema, name, outer) for member in members
        }
        if len(member_kinds) > 1:
            raise SchemaDefinitionError(
                f"Field `{name}` of schema `{schema.__qualname__}` mixes value types "
                f"and classes in `{annotation}`. Use a union of plain values, a union "
                "of classes, or `Any`."
            )
        kind = member_kinds.pop()
        if kind == "data" and (
            sum(is_mapping_type(member) for member in members) > 1
            or sum(is_sequence_type(member) for member in members) > 1
        ):
            raise SchemaDefinitionError(
                f"Field `{name}` of schema `{schema.__qualname__}` has `{annotation}`, "
                "whose mapping or list members cannot be told apart. Use at most one "
                "mapping type and one list type in a union, or `Any`."
            )
        return kind
    if annotation in (
        list,
        dict,
        tuple,
        collections.abc.Sequence,
        collections.abc.Mapping,
    ) or origin in (
        list,
        dict,
        tuple,
        collections.abc.Sequence,
        collections.abc.Mapping,
    ):
        items = [argument for argument in arguments if argument is not Ellipsis]
        if origin is dict or origin is collections.abc.Mapping:
            items = items[1:]
        kinds: set[FieldKind] = {
            _field_kind(item, schema, name, outer) for item in items
        }
        if kinds <= {"data"}:
            return "data"
        if kinds == {"object"} and origin in (list, dict):
            return "object"
        if kinds == {"any"}:
            return "any"
        raise SchemaDefinitionError(
            f"Field `{name}` of schema `{schema.__qualname__}` has `{annotation}`, "
            "but a container can hold either plain values or objects, and objects "
            "only in `list` and `dict`. Use `Any` otherwise."
        )
    if annotation in _UNSUPPORTED_CONTAINERS or origin in _UNSUPPORTED_CONTAINERS:
        raise SchemaDefinitionError(
            f"Field `{name}` of schema `{schema.__qualname__}` has the unsupported "
            f"container `{annotation}`. Use `list`, `dict`, `tuple` or `Any`."
        )
    if origin is None and isinstance(annotation, type):
        return "object"
    if isinstance(origin, type):
        return "object"
    raise SchemaDefinitionError(
        f"Field `{name}` of schema `{schema.__qualname__}` has the unsupported "
        f"annotation `{annotation}`."
    )


def _structure_default(factory: Callable[[], Any], plain: bool) -> Any:
    return _to_structure(factory(), plain)


def _to_structure(value: Any, plain: bool) -> Any:
    # A field that is `Any` in the structure takes plain containers: a dataclass
    # default there would stay typed and reject other union members.
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        items = {
            name: _to_structure(getattr(value, name), plain)
            for name in classify_fields(type(value))
        }
        return items if plain else derive_structure(type(value))(**items)
    if isinstance(value, (list, tuple)):
        return [_to_structure(item, plain) for item in value]
    if isinstance(value, dict):
        return {key: _to_structure(item, plain) for key, item in value.items()}
    return value


def _is_assignable(source: Any, target: Any) -> bool:
    while isinstance(source, TypeAliasType):
        source = source.__value__
    while isinstance(target, TypeAliasType):
        target = target.__value__
    if source is Any or target is Any:
        return True
    if get_origin(source) in (Union, types.UnionType):
        return all(_is_assignable(member, target) for member in get_args(source))
    if get_origin(target) in (Union, types.UnionType):
        return any(_is_assignable(source, member) for member in get_args(target))
    if get_origin(source) is not None or get_origin(target) is not None:
        return True
    if not (isinstance(source, type) and isinstance(target, type)):
        return True
    if target is float and source is int:
        return True
    if target is complex and source in (int, float):
        return True
    return issubclass(source, target)
