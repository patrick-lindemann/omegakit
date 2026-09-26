import dataclasses
import types
import typing
from collections.abc import Callable
from typing import Any, TypeAliasType, get_args, get_origin

from omegaconf import DictConfig, OmegaConf
from omegaconf.errors import OmegaConfBaseException

from .keys import CLASS_KEY, META_KEY, PARTIAL_KEY, REF_KEY
from .schema import (
    ConfigValidationError,
    check_schema,
    classify_fields,
    find_schema,
    validate_native,
)
from .utils import format_path, import_object


def validate(
    config: DictConfig | dict[str, Any], *, schema: type | None = None
) -> None:
    """Validate a loaded config without instantiating anything.

    The config is resolved, and every node with `$class` is checked bottom-up against
    the schema of its class. An object field accepts a node whose `$class` is the
    field's class or a subclass, or a `$ref` to an instance of it. Classes are
    imported to find their schemas, but nothing is built.

    Args:
        config: The assembled config, such as the result of `load_config`.
        schema: A dataclass the root of the config must match. Defaults to `None`.

    Raises:
        TypeError: If `schema` is not a dataclass.
        ConfigValidationError: If the config cannot be resolved or does not match a
            schema.
    """
    if schema is not None and not dataclasses.is_dataclass(schema):
        raise TypeError(f"`{schema.__qualname__}` is not a dataclass.")
    if not isinstance(config, DictConfig):
        config = OmegaConf.create(config)
    try:
        plain_config = OmegaConf.to_container(
            config, resolve=True, throw_on_missing=True
        )
    except OmegaConfBaseException as error:
        raise ConfigValidationError(
            f"Cannot resolve the config: {str(error).splitlines()[0]}"
        ) from error
    if schema is None:
        _check_untyped(plain_config, ())
    else:
        _check_object(plain_config, schema, ())


def is_valid(
    config: DictConfig | dict[str, Any], *, schema: type | None = None
) -> bool:
    """Check a loaded config like `validate`, without raising.

    Args:
        config: The assembled config, such as the result of `load_config`.
        schema: A dataclass the root of the config must match. Defaults to `None`.

    Returns:
        `True` if `validate` accepts the config, `False` otherwise.
    """
    try:
        validate(config, schema=schema)
    except ConfigValidationError:
        return False
    return True


def _check_untyped(value: Any, path: tuple[str | int, ...]) -> None:
    if isinstance(value, list):
        for index, item in enumerate(value):
            _check_untyped(item, (*path, index))
        return
    if not isinstance(value, dict):
        return
    value = {key: item for key, item in value.items() if key != META_KEY}
    if CLASS_KEY in value:
        _check_class_node(value, path)
    elif REF_KEY in value:
        _import_ref(value, path)
    else:
        for key, item in value.items():
            if isinstance(key, str) and key.startswith("$"):
                raise ConfigValidationError(
                    f"Key `{key}` in `{format_path(path)}` is not supported here; keys "
                    "starting with `$` are reserved."
                )
            _check_untyped(item, (*path, key))


def _check_class_node(node: dict[str, Any], path: tuple[str | int, ...]) -> Any:
    target = _import(node[CLASS_KEY], path)
    values = {}
    for key, value in node.items():
        if key == CLASS_KEY:
            continue
        if key == PARTIAL_KEY:
            if not isinstance(value, bool):
                raise ConfigValidationError(
                    f"`{PARTIAL_KEY}` in `{format_path(path)}` must be `true` or "
                    f"`false`, got `{value!r}`."
                )
            continue
        if isinstance(key, str) and key.startswith("$"):
            raise ConfigValidationError(
                f"Key `{key}` in `{format_path(path)}` is not supported next to "
                f"`{CLASS_KEY}`; keys starting with `$` are reserved."
            )
        values[key] = value
    schema = find_schema(target) if isinstance(target, type) else None
    if schema is None:
        for key, value in values.items():
            _check_untyped(value, (*path, key))
    else:
        check_schema(target)
        _check_section(schema, values, path)
    return target


def _check_section(
    schema: type, values: dict[str, Any], path: tuple[str | int, ...]
) -> None:
    for name, (kind, annotation) in classify_fields(schema).items():
        if name not in values or kind == "native":
            continue
        if kind == "any":
            _check_untyped(values[name], (*path, name))
        else:
            _check_object(values[name], annotation, (*path, name))
    validate_native(schema, values, path)


def _check_object(value: Any, annotation: Any, path: tuple[str | int, ...]) -> None:
    while isinstance(annotation, TypeAliasType):
        annotation = annotation.__value__
    if get_origin(annotation) in (typing.Union, types.UnionType):
        members = get_args(annotation)
    else:
        members = (annotation,)
    classes = tuple(
        member.__value__ if isinstance(member, TypeAliasType) else member
        for member in members
        if member is not type(None)
    )
    if value is None:
        if type(None) in members:
            return
        _check_type(isinstance, None, classes, path, "`None`")
        return
    if isinstance(value, dict):
        value = {key: item for key, item in value.items() if key != META_KEY}
        if CLASS_KEY in value:
            target = _check_class_node(value, path)
            if value.get(PARTIAL_KEY) is not True and isinstance(target, type):
                _check_type(
                    issubclass, target, classes, path, f"`$class: {value[CLASS_KEY]}`"
                )
            return
        if REF_KEY in value:
            target = _import_ref(value, path)
            _check_type(isinstance, target, classes, path, f"`$ref: {value[REF_KEY]}`")
            return
        for member in classes:
            if isinstance(member, type) and dataclasses.is_dataclass(member):
                _check_section(member, value, path)
                return
        _check_type(isinstance, value, classes, path, "a mapping without `$class`")
        return
    _check_type(isinstance, value, classes, path, f"`{value!r}`")


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
    except TypeError:
        return
    if not valid:
        expected = " | ".join(member.__qualname__ for member in classes)
        raise ConfigValidationError(
            f"`{format_path(path)}` expects {expected}, but the config gives {given}."
        )


def _import_ref(node: dict[str, Any], path: tuple[str | int, ...]) -> Any:
    if len(node) > 1:
        raise ConfigValidationError(
            f"A node using `{REF_KEY}` cannot contain any other keys, but "
            f"`{format_path(path)}` has {', '.join(map(repr, node))}."
        )
    return _import(node[REF_KEY], path)


def _import(import_path: str, path: tuple[str | int, ...]) -> Any:
    try:
        return import_object(import_path)
    except (ImportError, ValueError) as error:
        raise ConfigValidationError(
            f"Cannot import `{import_path}` in `{format_path(path)}`: {error}"
        ) from error
