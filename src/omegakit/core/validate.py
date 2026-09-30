import dataclasses
from collections.abc import Callable, Iterable
from typing import Any, TypeAliasType, get_args, get_origin

from omegaconf import MISSING, DictConfig, ListConfig, OmegaConf
from omegaconf.errors import OmegaConfBaseException

from .class_ import CLASS_KEY, import_class, split_arguments
from .configurable import find_schema
from .errors import ConfigValidationError
from .meta import drop_meta
from .ref import REF_KEY, import_ref
from .resolve import resolve_container
from .schema import (
    Schema,
    classify_fields,
    coerce_fields,
    find_section,
    split_union,
)
from .utils import (
    describe_error,
    describe_value,
    format_full_key,
    format_path,
)


@dataclasses.dataclass(frozen=True)
class Call:
    """A checked `$class` node, or a root checked against a class."""

    target: Any
    schema: Schema | None
    partial: bool
    arguments: dict[str, Any]
    path: tuple[str | int, ...]
    name: str


@dataclasses.dataclass(frozen=True)
class Section:
    """A checked mapping of a dataclass field without `$class`."""

    schema: Schema
    fields: dict[str, Any]
    path: tuple[str | int, ...]


@dataclasses.dataclass(frozen=True)
class Ref:
    """A checked `$ref` node."""

    target: Any


def validate(
    config: DictConfig | dict[str, Any],
    *,
    schema: type | None = None,
    allow_missing: bool = False,
    allowed_modules: Iterable[str] | None = None,
) -> None:
    """Check a loaded config against the schemas of the classes it names.

    Args:
        config: The assembled config.
        schema: The class the root of the config must match. Defaults to `None`.
        allow_missing: Accept `???`, required fields that are not given, and
            interpolations to missing or unknown keys. Defaults to `False`.
        allowed_modules: The modules, with their submodules, that `$class` and
            `$ref` may name. Defaults to `None`, which allows every module.

    Raises:
        ConfigValidationError: If the config cannot be resolved, does not match a
            schema, or names a module that is not allowed.
        SchemaDefinitionError: If `schema`, or a class that a `$class` names,
            cannot serve as a schema.
        TypeError: If `schema` is not a class, or `allowed_modules` is a string.
        ImportError: If a module that `$class` or `$ref` names fails to import a
            module of its own.
    """  # noqa: DOC502
    check(config, schema, allow_missing, allowed_modules)


def check(
    config: DictConfig | dict[str, Any],
    schema: type | None = None,
    allow_missing: bool = False,
    allowed_modules: Iterable[str] | None = None,
) -> Any:
    """Resolve a config and check it against the schemas of the classes it names.

    Args:
        config: The assembled config.
        schema: The class the root must match, as in `validate`. Defaults to `None`.
        allow_missing: Accept missing values, as in `validate`. Defaults to `False`.
        allowed_modules: The modules that `$class` and `$ref` may name, as in
            `validate`. Defaults to `None`.

    Returns:
        The checked config: its resolved values, with a `Call`, a `Section` or a
        `Ref` for each node that builds an object. A root that is checked against
        `schema` without a `$class` is a `Call` of `schema`.

    Raises:
        ConfigValidationError: If the config cannot be resolved, does not match a
            schema, or names a module that is not allowed.
        SchemaDefinitionError: If `schema`, or a class that a `$class` names,
            cannot serve as a schema.
        TypeError: If `schema` is not a class, or `allowed_modules` is a string.
        ImportError: If a module that `$class` or `$ref` names fails to import a
            module of its own.
    """  # noqa: DOC503
    if not isinstance(config, DictConfig):
        config = OmegaConf.create(config)
    plain_config = _resolve(config, allow_missing)
    if isinstance(allowed_modules, str):
        raise TypeError(
            f"`allowed_modules` must be a list of module names, not the string "
            f"`{allowed_modules!r}`."
        )
    if allowed_modules is not None:
        allowed_modules = tuple(allowed_modules)
    if schema is None:
        return _check_untyped(plain_config, (), allow_missing, allowed_modules)
    if not isinstance(schema, type):
        raise TypeError(f"`{schema!r}` is not a class.")
    name = f"{schema.__module__}.{schema.__qualname__}"
    if (
        isinstance(plain_config, dict)
        and CLASS_KEY not in plain_config
        and not dataclasses.is_dataclass(schema)
    ):
        if find_schema(schema) is None:
            raise ConfigValidationError(
                f"The root has no `{CLASS_KEY}`, and `{schema.__qualname__}` has no "
                "dataclass schema to check it against."
            )
        return _check_call(
            schema, plain_config, (), allow_missing, allowed_modules, name
        )
    checked = _check_object(plain_config, schema, (), allow_missing, allowed_modules)
    if isinstance(checked, Section):
        return Call(schema, find_schema(schema), False, checked.fields, (), name)
    return checked


def _resolve(config: DictConfig | ListConfig, allow_missing: bool) -> Any:
    try:
        return drop_meta(resolve_container(config, allow_missing))
    except OmegaConfBaseException as error:
        location = (
            f" `{format_full_key(error.full_key)}`" if error.full_key else " the config"
        )
        raise ConfigValidationError(
            f"Cannot resolve{location}: {describe_error(error)}"
        ) from error


def _check_untyped(
    value: Any,
    path: tuple[str | int, ...],
    allow_missing: bool,
    allowed_modules: tuple[str, ...] | None,
) -> Any:
    if isinstance(value, list):
        return [
            _check_untyped(item, (*path, index), allow_missing, allowed_modules)
            for index, item in enumerate(value)
        ]
    if not isinstance(value, dict):
        return value
    if CLASS_KEY in value:
        return _check_class_node(value, path, allow_missing, allowed_modules)
    if REF_KEY in value:
        return Ref(import_ref(value, path, allowed_modules))
    checked = {}
    for key, item in value.items():
        _check_not_reserved(key, path)
        checked[key] = _check_untyped(
            item, (*path, key), allow_missing, allowed_modules
        )
    return checked


def _check_not_reserved(key: Any, path: tuple[str | int, ...]) -> None:
    if isinstance(key, str) and key.startswith("$"):
        raise ConfigValidationError(
            f"Key `{key}` in `{format_path(path)}` is not supported here; keys "
            "starting with `$` are reserved."
        )


def _check_class_node(
    node: dict[str, Any],
    path: tuple[str | int, ...],
    allow_missing: bool,
    allowed_modules: tuple[str, ...] | None,
) -> Call:
    target = import_class(node, path, allowed_modules)
    return _check_call(
        target, node, path, allow_missing, allowed_modules, node[CLASS_KEY]
    )


def _check_call(
    target: Any,
    node: dict[str, Any],
    path: tuple[str | int, ...],
    allow_missing: bool,
    allowed_modules: tuple[str, ...] | None,
    name: str,
) -> Call:
    partial, arguments = split_arguments(node, path)
    schema = find_schema(target) if isinstance(target, type) else None
    if schema is None:
        arguments = {
            key: _check_untyped(value, (*path, key), allow_missing, allowed_modules)
            for key, value in arguments.items()
        }
    else:
        arguments = _check_section(
            schema, arguments, path, allow_missing, allowed_modules
        )
    return Call(target, schema, partial, arguments, path, name)


def _check_section(
    schema: Schema,
    values: dict[str, Any],
    path: tuple[str | int, ...],
    allow_missing: bool,
    allowed_modules: tuple[str, ...] | None,
) -> dict[str, Any]:
    # Data fields keep their values, which `coerce_fields` checks here and converts
    # when they are built.
    checked = dict(values)
    for name, (kind, annotation) in classify_fields(schema).items():
        if name not in values or kind == "data":
            continue
        if kind == "any":
            checked[name] = _check_untyped(
                values[name], (*path, name), allow_missing, allowed_modules
            )
        else:
            checked[name] = _check_object(
                values[name], annotation, (*path, name), allow_missing, allowed_modules
            )
    coerce_fields(schema, values, path, allow_missing)
    return checked


def _check_object(
    value: Any,
    annotation: Any,
    path: tuple[str | int, ...],
    allow_missing: bool,
    allowed_modules: tuple[str, ...] | None,
) -> Any:
    if allow_missing and value == MISSING:
        return value
    members, optional = split_union(annotation)
    classes = tuple(
        member.__value__ if isinstance(member, TypeAliasType) else member
        for member in members
    )
    if value is None:
        if not optional:
            _check_type(isinstance, None, classes, path, "`None`")
        return None
    if len(classes) == 1 and get_origin(classes[0]) in (list, dict):
        item_annotation = get_args(classes[0])[-1]
        if get_origin(classes[0]) is list and isinstance(value, list):
            return [
                _check_object(
                    item,
                    item_annotation,
                    (*path, index),
                    allow_missing,
                    allowed_modules,
                )
                for index, item in enumerate(value)
            ]
        if (
            get_origin(classes[0]) is dict
            and isinstance(value, dict)
            and CLASS_KEY not in value
            and REF_KEY not in value
        ):
            checked = {}
            for key, item in value.items():
                _check_not_reserved(key, path)
                checked[key] = _check_object(
                    item, item_annotation, (*path, key), allow_missing, allowed_modules
                )
            return checked
        raise ConfigValidationError(
            f"`{format_path(path)}` expects `{classes[0]}`, but the config gives "
            f"{describe_value(value)}."
        )
    if isinstance(value, dict):
        if CLASS_KEY in value:
            call = _check_class_node(value, path, allow_missing, allowed_modules)
            if not call.partial and isinstance(call.target, type):
                _check_type(
                    issubclass,
                    call.target,
                    classes,
                    path,
                    f"`$class: {value[CLASS_KEY]}`",
                )
            return call
        if REF_KEY in value:
            target = import_ref(value, path, allowed_modules)
            _check_type(isinstance, target, classes, path, f"`$ref: {value[REF_KEY]}`")
            return Ref(target)
        section = find_section(annotation)
        if section is not None:
            return Section(
                section,
                _check_section(section, value, path, allow_missing, allowed_modules),
                path,
            )
        _check_type(isinstance, value, classes, path, "a mapping without `$class`")
        return _check_untyped(value, path, allow_missing, allowed_modules)
    _check_type(isinstance, value, classes, path, describe_value(value))
    return _check_untyped(value, path, allow_missing, allowed_modules)


def _check_type(
    check: Callable[[Any, tuple[Any, ...]], bool],
    value: Any,
    classes: tuple[Any, ...],
    path: tuple[str | int, ...],
    given: str,
) -> None:
    if not all(isinstance(member, type) for member in classes):
        return
    try:
        valid = check(value, classes)
    # A `Protocol` that is not runtime-checkable rejects the check; it is skipped.
    except TypeError:
        return
    if not valid:
        expected = " | ".join(member.__qualname__ for member in classes)
        raise ConfigValidationError(
            f"`{format_path(path)}` expects {expected}, but the config gives {given}."
        )
