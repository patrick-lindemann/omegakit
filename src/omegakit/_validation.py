import dataclasses
import types
import typing
from collections.abc import Callable
from typing import Any, TypeAliasType, get_args, get_origin

from omegaconf import MISSING, DictConfig, ListConfig, OmegaConf
from omegaconf.errors import (
    InterpolationKeyError,
    InterpolationToMissingValueError,
    MissingMandatoryValue,
    OmegaConfBaseException,
)

from ._keys import CLASS_KEY, META_KEY, PARTIAL_KEY, REF_KEY
from ._schema import (
    ConfigValidationError,
    check_schema,
    classify_fields,
    find_schema,
    find_section,
    validate_native,
)
from ._utils import format_path, import_object


def validate(
    config: DictConfig | dict[str, Any],
    *,
    schema: type | None = None,
    allow_missing: bool = False,
) -> None:
    """Check a loaded config against the schemas of the classes it names.

    The config is resolved, and every node with `$class` is checked bottom-up against
    the schema of its class. An object field accepts a node whose `$class` is the
    field's class or a subclass, or a `$ref` to an instance of it.

    Validation checks values. It calls no `$class` target and constructs none of the
    schema's dataclasses. Code still runs: the modules named by `$class` and `$ref`
    are imported, resolvers run, so do `__instancecheck__` and `__subclasscheck__`
    of imported classes, and every `default_factory` of a schema runs, possibly
    several times and even for fields that the config sets. An exception from a
    factory propagates.

    Args:
        config: The assembled config, such as the result of `load_config`.
        schema: The class the root of the config must match. A dataclass checks the
            root as a section. Another class checks the root as a node that builds
            it: with `$class`, that class must be `schema` or a subclass; without,
            the root is checked against the schema of `schema`. Defaults to `None`.
        allow_missing: Accept missing values: `???`, required fields that are not
            given, and interpolations to missing or unknown keys, as in a library
            file that its consumers complete. Defaults to `False`.

    Raises:
        ConfigValidationError: If the config cannot be resolved or does not match a
            schema.
    """
    if not isinstance(config, DictConfig):
        config = OmegaConf.create(config)
    try:
        plain_config = resolve_config(config, allow_missing=allow_missing)
    except OmegaConfBaseException as error:
        location = f" `{error.full_key}`" if error.full_key else " the config"
        raise ConfigValidationError(
            f"Cannot resolve{location}: {str(error).splitlines()[0]}"
        ) from error
    check_resolved(plain_config, schema=schema, allow_missing=allow_missing)


def resolve_config(
    config: DictConfig | ListConfig, *, allow_missing: bool = False
) -> Any:
    """Resolve a config into plain containers.

    Args:
        config: The config to resolve.
        allow_missing: Give `???` for missing values and for interpolations to
            missing or unknown keys, instead of raising. Defaults to `False`.

    Returns:
        The resolved config as `dict`s and `list`s.
    """
    if not allow_missing:
        return OmegaConf.to_container(config, resolve=True, throw_on_missing=True)
    return _resolve_allowing_missing(config)


def check_resolved(
    config: Any, *, schema: type | None = None, allow_missing: bool = False
) -> None:
    """Check a resolved config, the plain containers of `resolve_config`.

    Args:
        config: The resolved config.
        schema: The class the root must match, as in `validate`. Defaults to `None`.
        allow_missing: Accept missing values, as in `validate`. Defaults to `False`.

    Raises:
        TypeError: If `schema` is not a class.
        ConfigValidationError: If the config does not match a schema.
    """
    if schema is None:
        _check_untyped(config, (), allow_missing)
        return
    if not isinstance(schema, type):
        raise TypeError(f"`{schema!r}` is not a class.")
    if (
        isinstance(config, dict)
        and CLASS_KEY not in config
        and not dataclasses.is_dataclass(schema)
    ):
        section = find_schema(schema)
        if section is None:
            raise ConfigValidationError(
                f"The root has no `{CLASS_KEY}`, and `{schema.__qualname__}` has no "
                "dataclass schema to check it against."
            )
        _check_target(schema, config, (), allow_missing)
        return
    _check_object(config, schema, (), allow_missing)


def _resolve_allowing_missing(container: DictConfig | ListConfig) -> Any:
    if isinstance(container, ListConfig):
        return [_resolve_item(container, index) for index in range(len(container))]
    return {key: _resolve_item(container, key) for key in container}


def _resolve_item(container: Any, key: Any) -> Any:
    try:
        value = container[key]
    except (
        MissingMandatoryValue,
        InterpolationToMissingValueError,
        InterpolationKeyError,
    ):
        return MISSING
    if isinstance(value, (DictConfig, ListConfig)):
        return _resolve_allowing_missing(value)
    return value


def _check_untyped(
    value: Any, path: tuple[str | int, ...], allow_missing: bool
) -> None:
    if isinstance(value, list):
        for index, item in enumerate(value):
            _check_untyped(item, (*path, index), allow_missing)
        return
    if not isinstance(value, dict):
        return
    value = {key: item for key, item in value.items() if key != META_KEY}
    if CLASS_KEY in value:
        _check_class_node(value, path, allow_missing)
    elif REF_KEY in value:
        _import_ref(value, path)
    else:
        for key, item in value.items():
            if isinstance(key, str) and key.startswith("$"):
                raise ConfigValidationError(
                    f"Key `{key}` in `{format_path(path)}` is not supported here; keys "
                    "starting with `$` are reserved."
                )
            _check_untyped(item, (*path, key), allow_missing)


def _check_class_node(
    node: dict[str, Any], path: tuple[str | int, ...], allow_missing: bool
) -> Any:
    target = _import(node, CLASS_KEY, path)
    if not (callable(target) or hasattr(target, "from_config")):
        raise ConfigValidationError(
            f"`{CLASS_KEY}: {node[CLASS_KEY]}` in `{format_path(path)}` is neither "
            f"callable nor has `from_config`. Use `{REF_KEY}` for an object that is "
            "used as it is."
        )
    _check_target(target, node, path, allow_missing)
    return target


def _check_target(
    target: Any, node: dict[str, Any], path: tuple[str | int, ...], allow_missing: bool
) -> None:
    values = {}
    for key, value in node.items():
        if key in (CLASS_KEY, META_KEY):
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
            _check_untyped(value, (*path, key), allow_missing)
    else:
        check_schema(target)
        _check_section(schema, values, path, allow_missing)


def _check_section(
    schema: type,
    values: dict[str, Any],
    path: tuple[str | int, ...],
    allow_missing: bool,
) -> None:
    for name, (kind, annotation) in classify_fields(schema).items():
        if name not in values or kind == "native":
            continue
        if kind == "any":
            _check_untyped(values[name], (*path, name), allow_missing)
        else:
            _check_object(values[name], annotation, (*path, name), allow_missing)
    validate_native(schema, values, path, allow_missing)


def _check_object(
    value: Any, annotation: Any, path: tuple[str | int, ...], allow_missing: bool
) -> None:
    if allow_missing and value == MISSING:
        return
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
    if len(classes) == 1 and get_origin(classes[0]) in (list, dict):
        item_annotation = get_args(classes[0])[-1]
        if get_origin(classes[0]) is list and isinstance(value, list):
            for index, item in enumerate(value):
                _check_object(item, item_annotation, (*path, index), allow_missing)
            return
        if (
            get_origin(classes[0]) is dict
            and isinstance(value, dict)
            and CLASS_KEY not in value
            and REF_KEY not in value
        ):
            _check_untyped({key: None for key in value}, path, allow_missing)
            for key, item in value.items():
                if key != META_KEY:
                    _check_object(item, item_annotation, (*path, key), allow_missing)
            return
        raise ConfigValidationError(
            f"`{format_path(path)}` expects `{classes[0]}`, but the config gives "
            f"{value!r}."
        )
    if isinstance(value, dict):
        value = {key: item for key, item in value.items() if key != META_KEY}
        if CLASS_KEY in value:
            target = _check_class_node(value, path, allow_missing)
            if value.get(PARTIAL_KEY) is not True and isinstance(target, type):
                _check_type(
                    issubclass, target, classes, path, f"`$class: {value[CLASS_KEY]}`"
                )
            return
        if REF_KEY in value:
            target = _import_ref(value, path)
            _check_type(isinstance, target, classes, path, f"`$ref: {value[REF_KEY]}`")
            return
        section = find_section(annotation)
        if section is not None:
            _check_section(section, value, path, allow_missing)
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
    return _import(node, REF_KEY, path)


def _import(node: dict[str, Any], key: str, path: tuple[str | int, ...]) -> Any:
    import_path = node[key]
    if not isinstance(import_path, str):
        raise ConfigValidationError(
            f"`{key}` in `{format_path(path)}` must be an import path, such as "
            f"`package.module.Name`, but the config gives `{import_path!r}`."
        )
    try:
        return import_object(import_path)
    except ImportError as error:
        raise ConfigValidationError(
            f"Cannot import `{import_path}` in `{format_path(path)}`: {error}"
        ) from error
