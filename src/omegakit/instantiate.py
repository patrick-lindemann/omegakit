import functools
from collections.abc import Callable, Iterable
from typing import Any, cast, get_args, get_origin, overload

from omegaconf import DictConfig, ListConfig, OmegaConf

from .errors import ConfigValidationError
from .keys import CLASS_KEY, META_KEY, PARTIAL_KEY, REF_KEY
from .loading import merge_overrides
from .schema import (
    check_schema,
    classify_fields,
    find_schema,
    find_section,
    union_members,
    validate_native,
)
from .utils import format_path, import_object
from .validation import check_resolved, resolve_config


@overload
def instantiate(
    config: DictConfig | dict[str, Any],
    *,
    overrides: DictConfig | dict[str, Any] | list[str] | None = None,
    allowed_modules: Iterable[str] | None = None,
) -> Any: ...


@overload
def instantiate[T](
    config: DictConfig | dict[str, Any],
    *,
    schema: type[T],
    overrides: DictConfig | dict[str, Any] | list[str] | None = None,
    allowed_modules: Iterable[str] | None = None,
) -> T: ...


def instantiate(
    config: DictConfig | dict[str, Any],
    *,
    schema: type[Any] | None = None,
    overrides: DictConfig | dict[str, Any] | list[str] | None = None,
    allowed_modules: Iterable[str] | None = None,
) -> Any:
    """Build the object that a config node describes.

    The node is resolved and validated as `validate` does, and a problem raises
    `ConfigValidationError` before any configured class is called. Then the node is
    built children first: `$class` is called, or its `from_config` when it has one,
    `$ref` is imported, and `$partial: true` gives a `functools.partial`.

    Args:
        config: The node to build. It must have `$class`, unless `schema` is given.
        schema: The class to build. A root with `$class` must name `schema` or a
            subclass. A root without `$class` is built as if its `$class` named
            `schema`: a dataclass gives an instance of itself, and a `Configurable`
            is built through `from_config`. Defaults to `None`, which builds the
            root's `$class`.
        overrides: Values merged into the node first, as in `load_config`. Defaults
            to `None`.
        allowed_modules: The modules that `$class` and `$ref` may name, as in
            `validate`. Defaults to `None`, which allows every module.

    Returns:
        The built object.

    Raises:
        ConfigValidationError: If the node has neither `$class` nor `schema`, or
            does not match a schema.
        ConfigLoadError: If an override is invalid.
        SchemaDefinitionError: If `schema`, or a class that a `$class` names,
            cannot serve as a schema.
        TypeError: If `schema` is not a class.
    """  # noqa: DOC502
    return _instantiate(config, schema, overrides, allowed_modules)


@overload
def prepare(
    config: DictConfig | dict[str, Any],
    *,
    overrides: DictConfig | dict[str, Any] | list[str] | None = None,
    allowed_modules: Iterable[str] | None = None,
) -> functools.partial[Any]: ...


@overload
def prepare[T](
    config: DictConfig | dict[str, Any],
    *,
    schema: type[T],
    overrides: DictConfig | dict[str, Any] | list[str] | None = None,
    allowed_modules: Iterable[str] | None = None,
) -> functools.partial[T]: ...


def prepare(
    config: DictConfig | dict[str, Any],
    *,
    schema: type[Any] | None = None,
    overrides: DictConfig | dict[str, Any] | list[str] | None = None,
    allowed_modules: Iterable[str] | None = None,
) -> functools.partial[Any]:
    """Build a config node's children, and defer the call of the node itself.

    Like `instantiate`, the node is validated first and its children are built; the
    node's own `$class`, or its `from_config`, is wrapped in a `functools.partial`
    that takes more keyword arguments when called.

    Args:
        config: The node to prepare. It must have `$class`, unless `schema` is
            given.
        schema: The class that the partial builds, as in `instantiate`. Defaults to
            `None`, which builds the root's `$class`.
        overrides: Values merged into the node first, as in `load_config`. Defaults
            to `None`.
        allowed_modules: The modules that `$class` and `$ref` may name, as in
            `validate`. Defaults to `None`, which allows every module.

    Returns:
        The partial that builds the object.

    Raises:
        ConfigValidationError: If the node has neither `$class` nor `schema`, or
            does not match a schema.
        ConfigLoadError: If an override is invalid.
        SchemaDefinitionError: If `schema`, or a class that a `$class` names,
            cannot serve as a schema.
        TypeError: If `schema` is not a class.
    """  # noqa: DOC502
    return _instantiate(
        config, schema, overrides, allowed_modules, wrap=functools.partial
    )


def _instantiate(
    config: DictConfig | dict[str, Any],
    schema: type | None,
    overrides: DictConfig | dict[str, Any] | list[str] | None,
    allowed_modules: Iterable[str] | None,
    wrap: Callable | None = None,
) -> Any:
    if CLASS_KEY not in config and (schema is None or REF_KEY in config):
        raise ConfigValidationError(
            f"`{format_path(())}` has no `{CLASS_KEY}`, so there is nothing to "
            "instantiate."
        )
    if not isinstance(config, DictConfig):
        config = OmegaConf.create(config)
    if overrides is not None:
        config = config.copy()
        merge_overrides(config, overrides)
    plain_config = cast(dict[str, Any], resolve_config(config))
    check_resolved(plain_config, schema=schema, allowed_modules=allowed_modules)
    if CLASS_KEY in plain_config:
        return _build(plain_config, wrap)
    return _build(plain_config, wrap, target=schema)


def _build(
    plain_config: dict[str, Any],
    wrap: Callable | None = None,
    path: tuple[str | int, ...] = (),
    target: Any = None,
) -> Any:
    # `target` stands in for the `$class` of a root that has none.
    cls = import_object(plain_config[CLASS_KEY]) if target is None else target
    schema = find_schema(cls) if isinstance(cls, type) else None
    if schema is not None:
        check_schema(cls)
    values = {}
    for key, value in plain_config.items():
        if key in (CLASS_KEY, META_KEY):
            continue
        if key == PARTIAL_KEY:
            if value:
                wrap = functools.partial
            continue
        values[key] = value
    if schema is None:
        config = {
            key: _materialize(value, (*path, key)) for key, value in values.items()
        }
    elif schema is cls:
        config = _build_fields(schema, values, path)
    else:
        config = schema(**_build_fields(schema, values, path))
    try:
        if hasattr(cls, "from_config"):
            return (
                wrap(cls.from_config, config)
                if wrap is not None
                else cls.from_config(config)
            )
        return wrap(cls, **config) if wrap is not None else cls(**config)
    except Exception as error:
        name = plain_config.get(CLASS_KEY, f"{cls.__module__}.{cls.__qualname__}")
        error.add_note(f"while instantiating {format_path(path)} ({name})")
        raise


def _build_fields(
    schema: type, values: dict[str, Any], path: tuple[str | int, ...]
) -> dict[str, Any]:
    fields = validate_native(schema, values, path, build=True)
    for name, (kind, annotation) in classify_fields(schema).items():
        if kind == "native" or name not in values:
            continue
        if kind == "object":
            fields[name] = _build_object(values[name], annotation, (*path, name))
        else:
            fields[name] = _materialize(values[name], (*path, name))
    return fields


def _build_object(value: Any, annotation: Any, path: tuple[str | int, ...]) -> Any:
    # Follows the annotation into `list` and `dict` fields, where a plain mapping in a
    # dataclass item is a section, as in `validate`.
    members, _ = union_members(annotation)
    if len(members) == 1 and get_origin(members[0]) in (list, dict):
        item_annotation = get_args(members[0])[-1]
        if isinstance(value, list):
            return [
                _build_object(item, item_annotation, (*path, index))
                for index, item in enumerate(value)
            ]
        if isinstance(value, dict):
            return {
                key: _build_object(item, item_annotation, (*path, key))
                for key, item in value.items()
                if key != META_KEY
            }
    section = (
        find_section(annotation)
        if isinstance(value, dict) and CLASS_KEY not in value and REF_KEY not in value
        else None
    )
    if section is None:
        return _materialize(value, path)
    return section(
        **_build_fields(
            section, {key: item for key, item in value.items() if key != META_KEY}, path
        )
    )


def _materialize(node: Any, path: tuple[str | int, ...]) -> Any:
    if isinstance(node, (dict, DictConfig)):
        node = {k: v for k, v in node.items() if k != META_KEY}
        if CLASS_KEY in node:
            return _build(node, path=path)
        if REF_KEY in node:
            return import_object(node[REF_KEY])
        return {k: _materialize(v, (*path, k)) for k, v in node.items()}
    if isinstance(node, (list, ListConfig)):
        return [_materialize(v, (*path, index)) for index, v in enumerate(node)]
    return node
