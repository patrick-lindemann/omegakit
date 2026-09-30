import functools
from collections.abc import Iterable
from typing import Any, overload

from omegaconf import DictConfig, OmegaConf

from .class_ import CLASS_KEY, call
from .errors import ConfigValidationError
from .override import merge_overrides
from .ref import REF_KEY
from .schema import Schema, classify_fields, coerce_fields
from .utils import format_path
from .validate import Call, Ref, Section, check


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

    Args:
        config: The node to build. It must have `$class`, unless `schema` is given.
        schema: The class to build. Defaults to `None`, which builds the root's
            `$class`.
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
        TypeError: If `schema` is not a class, `overrides` is not a `DictConfig`, a
            `dict` or a `list` of strings, or `allowed_modules` is a string.
        ImportError: If a module that `$class` or `$ref` names fails to import a
            module of its own.
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
        TypeError: If `schema` is not a class, `overrides` is not a `DictConfig`, a
            `dict` or a `list` of strings, or `allowed_modules` is a string.
        ImportError: If a module that `$class` or `$ref` names fails to import a
            module of its own.
    """  # noqa: DOC502
    return _instantiate(config, schema, overrides, allowed_modules, partial=True)


def _instantiate(
    config: DictConfig | dict[str, Any],
    schema: type | None,
    overrides: DictConfig | dict[str, Any] | list[str] | None,
    allowed_modules: Iterable[str] | None,
    partial: bool = False,
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
    return _build(check(config, schema, allowed_modules=allowed_modules), partial)


def _build(value: Any, partial: bool = False) -> Any:
    if isinstance(value, Call):
        if value.schema is None:
            config = {key: _build(item) for key, item in value.arguments.items()}
        elif value.schema is value.target:
            config = _build_fields(value.schema, value.arguments, value.path)
        else:
            config = value.schema(
                **_build_fields(value.schema, value.arguments, value.path)
            )
        return call(
            value.target, config, partial or value.partial, value.path, value.name
        )
    if isinstance(value, Section):
        return value.schema(**_build_fields(value.schema, value.fields, value.path))
    if isinstance(value, Ref):
        return value.target
    if isinstance(value, dict):
        return {key: _build(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_build(item) for item in value]
    return value


def _build_fields(
    schema: Schema, values: dict[str, Any], path: tuple[str | int, ...]
) -> dict[str, Any]:
    fields = coerce_fields(schema, values, path, build=True)
    for name, (kind, _) in classify_fields(schema).items():
        if kind != "data" and name in values:
            fields[name] = _build(values[name])
    return fields
