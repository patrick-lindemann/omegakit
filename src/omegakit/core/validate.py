import dataclasses
from collections.abc import Callable, Iterable
from typing import Any, TypeAliasType, get_args, get_origin

from omegaconf import MISSING, DictConfig, ListConfig, OmegaConf
from omegaconf.errors import (
    InterpolationKeyError,
    InterpolationToMissingValueError,
    MissingMandatoryValue,
    OmegaConfBaseException,
)

from .assembly import META_KEY
from .errors import ConfigValidationError
from .keys import CLASS_KEY, PARTIAL_KEY, REF_KEY
from .schemas import (
    check_schema,
    classify_fields,
    coerce_fields,
    find_schema,
    find_section,
    split_union,
)
from .utils import (
    describe_error,
    describe_value,
    format_full_key,
    format_path,
    import_object,
)


def validate(
    config: DictConfig | dict[str, Any],
    *,
    schema: type | None = None,
    allow_missing: bool = False,
    allowed_modules: Iterable[str] | None = None,
) -> None:
    """Check a loaded config against the schemas of the classes it names.

    Args:
        config: The assembled config, such as the result of `load_config`.
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
            module of its own, such as a missing dependency.
    """  # noqa: DOC502
    if not isinstance(config, DictConfig):
        config = OmegaConf.create(config)
    plain_config = resolve_config(config, allow_missing=allow_missing)
    check_resolved(
        plain_config,
        schema=schema,
        allow_missing=allow_missing,
        allowed_modules=allowed_modules,
    )


def resolve_config(config: DictConfig | ListConfig, allow_missing: bool = False) -> Any:
    """Resolve a config into plain containers.

    Args:
        config: The config to resolve.
        allow_missing: Give `???` for missing values and for interpolations to
            missing or unknown keys, instead of raising. Defaults to `False`.

    Returns:
        The resolved config as `dict`s and `list`s.

    Raises:
        ConfigValidationError: If a value is missing or an interpolation fails,
            including an exception from a resolver. OmegaConf's error is the cause.
    """
    try:
        if not allow_missing:
            return OmegaConf.to_container(config, resolve=True, throw_on_missing=True)
        return _resolve_allowing_missing(config)
    except OmegaConfBaseException as error:
        location = (
            f" `{format_full_key(error.full_key)}`" if error.full_key else " the config"
        )
        raise ConfigValidationError(
            f"Cannot resolve{location}: {describe_error(error)}"
        ) from error


def check_resolved(
    config: Any,
    schema: type | None = None,
    allow_missing: bool = False,
    allowed_modules: Iterable[str] | None = None,
) -> None:
    """Check a resolved config, the plain containers of `resolve_config`.

    Args:
        config: The resolved config.
        schema: The class the root must match, as in `validate`. Defaults to `None`.
        allow_missing: Accept missing values, as in `validate`. Defaults to `False`.
        allowed_modules: The modules that `$class` and `$ref` may name, as in
            `validate`. Defaults to `None`.

    Raises:
        TypeError: If `schema` is not a class, or `allowed_modules` is a string.
        ConfigValidationError: If the config does not match a schema.
        SchemaDefinitionError: If `schema`, or a class that a `$class` names,
            cannot serve as a schema.
        ImportError: If a module that `$class` or `$ref` names fails to import a
            module of its own, such as a missing dependency.
    """  # noqa: DOC503
    if isinstance(allowed_modules, str):
        raise TypeError(
            f"`allowed_modules` must be a list of module names, not the string "
            f"`{allowed_modules!r}`."
        )
    if allowed_modules is not None:
        allowed_modules = tuple(allowed_modules)
    if schema is None:
        _check_untyped(config, (), allow_missing, allowed_modules)
        return
    if not isinstance(schema, type):
        raise TypeError(f"`{schema!r}` is not a class.")
    if (
        isinstance(config, dict)
        and CLASS_KEY not in config
        and not dataclasses.is_dataclass(schema)
    ):
        if find_schema(schema) is None:
            raise ConfigValidationError(
                f"The root has no `{CLASS_KEY}`, and `{schema.__qualname__}` has no "
                "dataclass schema to check it against."
            )
        _check_target(schema, config, (), allow_missing, allowed_modules)
        return
    _check_object(config, schema, (), allow_missing, allowed_modules)


def resolve_item(container: Any, key: Any) -> Any:
    """Resolve one item of a container, giving `???` for a missing value.

    Args:
        container: The `DictConfig` or `ListConfig`.
        key: The item's key or index.

    Returns:
        The resolved item, with containers as `dict`s and `list`s, or `???` for a
        missing value and for an interpolation to a missing or unknown key.
    """
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


def _resolve_allowing_missing(container: DictConfig | ListConfig) -> Any:
    if isinstance(container, ListConfig):
        return [resolve_item(container, index) for index in range(len(container))]
    return {key: resolve_item(container, key) for key in container}


def _check_untyped(
    value: Any,
    path: tuple[str | int, ...],
    allow_missing: bool,
    allowed_modules: tuple[str, ...] | None,
) -> None:
    if isinstance(value, list):
        for index, item in enumerate(value):
            _check_untyped(item, (*path, index), allow_missing, allowed_modules)
        return
    if not isinstance(value, dict):
        return
    value = {key: item for key, item in value.items() if key != META_KEY}
    if CLASS_KEY in value:
        _check_class_node(value, path, allow_missing, allowed_modules)
    elif REF_KEY in value:
        _import_ref(value, path, allowed_modules)
    else:
        for key, item in value.items():
            _check_not_reserved(key, path)
            _check_untyped(item, (*path, key), allow_missing, allowed_modules)


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
) -> Any:
    target = _import(node, CLASS_KEY, path, allowed_modules)
    if not (callable(target) or hasattr(target, "from_config")):
        raise ConfigValidationError(
            f"`{CLASS_KEY}: {node[CLASS_KEY]}` in `{format_path(path)}` is neither "
            f"callable nor has `from_config`. Use `{REF_KEY}` for an object that is "
            "used as it is."
        )
    _check_target(target, node, path, allow_missing, allowed_modules)
    return target


def _check_target(
    target: Any,
    node: dict[str, Any],
    path: tuple[str | int, ...],
    allow_missing: bool,
    allowed_modules: tuple[str, ...] | None,
) -> None:
    values = {}
    for key, value in node.items():
        if key in (CLASS_KEY, META_KEY):
            continue
        if key == PARTIAL_KEY:
            if not isinstance(value, bool):
                raise ConfigValidationError(
                    f"`{PARTIAL_KEY}` in `{format_path(path)}` must be `true` or "
                    f"`false`, but the config gives {describe_value(value)}."
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
            _check_untyped(value, (*path, key), allow_missing, allowed_modules)
    else:
        check_schema(target)
        _check_section(schema, values, path, allow_missing, allowed_modules)


def _check_section(
    schema: type,
    values: dict[str, Any],
    path: tuple[str | int, ...],
    allow_missing: bool,
    allowed_modules: tuple[str, ...] | None,
) -> None:
    for name, (kind, annotation) in classify_fields(schema).items():
        if name not in values or kind == "data":
            continue
        if kind == "any":
            _check_untyped(values[name], (*path, name), allow_missing, allowed_modules)
        else:
            _check_object(
                values[name], annotation, (*path, name), allow_missing, allowed_modules
            )
    coerce_fields(schema, values, path, allow_missing)


def _check_object(
    value: Any,
    annotation: Any,
    path: tuple[str | int, ...],
    allow_missing: bool,
    allowed_modules: tuple[str, ...] | None,
) -> None:
    if allow_missing and value == MISSING:
        return
    members, optional = split_union(annotation)
    classes = tuple(
        member.__value__ if isinstance(member, TypeAliasType) else member
        for member in members
    )
    if value is None:
        if optional:
            return
        _check_type(isinstance, None, classes, path, "`None`")
        return
    if len(classes) == 1 and get_origin(classes[0]) in (list, dict):
        item_annotation = get_args(classes[0])[-1]
        if get_origin(classes[0]) is list and isinstance(value, list):
            for index, item in enumerate(value):
                _check_object(
                    item,
                    item_annotation,
                    (*path, index),
                    allow_missing,
                    allowed_modules,
                )
            return
        if (
            get_origin(classes[0]) is dict
            and isinstance(value, dict)
            and CLASS_KEY not in value
            and REF_KEY not in value
        ):
            for key, item in value.items():
                if key != META_KEY:
                    _check_not_reserved(key, path)
                    _check_object(
                        item,
                        item_annotation,
                        (*path, key),
                        allow_missing,
                        allowed_modules,
                    )
            return
        raise ConfigValidationError(
            f"`{format_path(path)}` expects `{classes[0]}`, but the config gives "
            f"{describe_value(value)}."
        )
    if isinstance(value, dict):
        value = {key: item for key, item in value.items() if key != META_KEY}
        if CLASS_KEY in value:
            target = _check_class_node(value, path, allow_missing, allowed_modules)
            if value.get(PARTIAL_KEY) is not True and isinstance(target, type):
                _check_type(
                    issubclass, target, classes, path, f"`$class: {value[CLASS_KEY]}`"
                )
            return
        if REF_KEY in value:
            target = _import_ref(value, path, allowed_modules)
            _check_type(isinstance, target, classes, path, f"`$ref: {value[REF_KEY]}`")
            return
        section = find_section(annotation)
        if section is not None:
            _check_section(section, value, path, allow_missing, allowed_modules)
            return
        _check_type(isinstance, value, classes, path, "a mapping without `$class`")
        _check_untyped(value, path, allow_missing, allowed_modules)
        return
    _check_type(isinstance, value, classes, path, describe_value(value))
    _check_untyped(value, path, allow_missing, allowed_modules)


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


def _import_ref(
    node: dict[str, Any],
    path: tuple[str | int, ...],
    allowed_modules: tuple[str, ...] | None,
) -> Any:
    if len(node) > 1:
        raise ConfigValidationError(
            f"A node using `{REF_KEY}` cannot contain any other keys, but "
            f"`{format_path(path)}` has {', '.join(f'`{key}`' for key in node)}."
        )
    return _import(node, REF_KEY, path, allowed_modules)


def _import(
    node: dict[str, Any],
    key: str,
    path: tuple[str | int, ...],
    allowed_modules: tuple[str, ...] | None,
) -> Any:
    import_path = node[key]
    if not isinstance(import_path, str):
        raise ConfigValidationError(
            f"`{key}` in `{format_path(path)}` must be an import path, such as "
            "`package.module.Name`, but the config gives "
            f"{describe_value(import_path)}."
        )
    # Checked before the import, so that a module that is not allowed never runs.
    if not _is_allowed(import_path.rpartition(".")[0], allowed_modules):
        raise ConfigValidationError(
            f"`{key}: {import_path}` in `{format_path(path)}` names a module that "
            "is not in `allowed_modules`."
        )
    try:
        target = import_object(import_path)
    except ImportError as error:
        # A module that the target's own module fails to import is a missing
        # dependency, not a mistake in the config.
        parts = import_path.split(".")
        targets = {".".join(parts[:end]) for end in range(1, len(parts))}
        if error.name != import_path and not (
            isinstance(error, ModuleNotFoundError) and error.name in targets
        ):
            raise
        raise ConfigValidationError(
            f"Cannot import `{import_path}` in `{format_path(path)}`: {error}"
        ) from error
    # An allowed module can import a name from a module that is not allowed.
    module = getattr(target, "__module__", None)
    if isinstance(module, str) and not _is_allowed(module, allowed_modules):
        raise ConfigValidationError(
            f"`{key}: {import_path}` in `{format_path(path)}` is defined in "
            f"`{module}`, which is not in `allowed_modules`."
        )
    return target


def _is_allowed(module: str, allowed_modules: tuple[str, ...] | None) -> bool:
    return allowed_modules is None or any(
        module == allowed or module.startswith(f"{allowed}.")
        for allowed in allowed_modules
    )
