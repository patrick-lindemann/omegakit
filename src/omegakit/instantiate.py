from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any, cast, overload

from omegaconf import DictConfig, ListConfig, OmegaConf

from .keys import CLASS_KEY, META_KEY, PARTIAL_KEY, REF_KEY
from .loading import parse_overrides
from .schema import (
    check_object,
    check_schema,
    classify_fields,
    find_schema,
    validate_native,
)
from .utils import format_path, import_object


@overload
def instantiate(
    config: DictConfig | dict[str, Any],
    *,
    overrides: DictConfig | dict[str, Any] | list[str] | None = None,
) -> Any: ...


@overload
def instantiate[T](
    config: DictConfig | dict[str, Any],
    expected: type[T],
    *,
    overrides: DictConfig | dict[str, Any] | list[str] | None = None,
) -> T: ...


def instantiate(
    config: DictConfig | dict[str, Any],
    expected: type[Any] | None = None,
    *,
    overrides: DictConfig | dict[str, Any] | list[str] | None = None,
) -> Any:
    """Instantiate an object from a configuration.

    Args:
        config: The configuration.
        expected: The expected type of the instantiated object. It is a static typing
            hint only and is not checked at runtime. Defaults to `None`.
        overrides: Additional argument overrides. Can be provided as a DictConfig, a
            regular dictionary, or a list of `key=value` strings (e.g.
            `["foo=1.0", "bar=baz"]`). Defaults to `None`.

    Returns:
        The instantiated object.
    """
    return _instantiate(config, overrides)


@overload
def prepare(
    config: DictConfig | dict[str, Any],
    *,
    overrides: DictConfig | dict[str, Any] | list[str] | None = None,
) -> functools.partial[Any]: ...


@overload
def prepare[T](
    config: DictConfig | dict[str, Any],
    expected: type[T],
    *,
    overrides: DictConfig | dict[str, Any] | list[str] | None = None,
) -> functools.partial[T]: ...


def prepare(
    config: DictConfig | dict[str, Any],
    expected: type[Any] | None = None,
    *,
    overrides: DictConfig | dict[str, Any] | list[str] | None = None,
) -> functools.partial[Any]:
    """Prepare an object for instantiation from a configuration.

    The resulting function can be called later to perform the actual instantiation with
    extra arguments.

    Args:
        config: The configuration.
        expected: The expected type of the instantiated object. It is a static typing
            hint only and is not checked at runtime. Defaults to `None`.
        overrides: Additional argument overrides. Can be provided as a DictConfig, a
            regular dictionary, or a list of `key=value` strings (e.g.
            `["foo=1.0", "bar=baz"]`). Defaults to `None`.

    Returns:
        The instantiating function.
    """
    return _instantiate(config, overrides, wrap=functools.partial)


def _instantiate(
    config: DictConfig | dict[str, Any],
    overrides: DictConfig | dict[str, Any] | list[str] | None = None,
    wrap: Callable | None = None,
) -> Any:
    if CLASS_KEY not in config:
        raise ValueError(
            f"Cannot instantiate config with no `{CLASS_KEY}` key:"
            f"\n{OmegaConf.to_yaml(config)}"
        )
    if not isinstance(config, DictConfig):
        config = OmegaConf.create(config)
    if overrides is not None:
        config = config.copy()
        overrides = parse_overrides(overrides)
        config.merge_with(overrides)
    plain_config = cast(
        dict[str, Any],
        OmegaConf.to_container(config, resolve=True, throw_on_missing=True),
    )
    return _build(plain_config, wrap)


def _build(
    plain_config: dict[str, Any],
    wrap: Callable | None = None,
    path: tuple[str | int, ...] = (),
) -> Any:
    cls = import_object(plain_config[CLASS_KEY])
    schema = find_schema(cls) if isinstance(cls, type) else None
    if schema is not None:
        check_schema(cls)
    values = {}
    for key, value in plain_config.items():
        if key in (CLASS_KEY, META_KEY):
            continue
        if isinstance(key, str) and key.startswith("$") and key != PARTIAL_KEY:
            raise ValueError(
                f"Invalid config node with `{CLASS_KEY}` key: {plain_config}. Key "
                f"`{key}` is not supported here; keys starting with `$` are reserved."
            )
        if key == PARTIAL_KEY:
            if not isinstance(value, bool):
                raise ValueError(
                    f"`{PARTIAL_KEY}` must be `true` or `false`, got `{value!r}`."
                )
            if value:
                wrap = functools.partial
            continue
        values[key] = value
    if schema is None:
        config = {
            key: _materialize(value, (*path, key)) for key, value in values.items()
        }
    else:
        config = _build_typed_config(schema, values, path)
    try:
        if hasattr(cls, "from_config"):
            return (
                wrap(cls.from_config, config)
                if wrap is not None
                else cls.from_config(config)
            )
        return wrap(cls, **config) if wrap is not None else cls(**config)
    except Exception as error:
        error.add_note(
            f"while instantiating {format_path(path)} ({plain_config[CLASS_KEY]})"
        )
        raise


def _build_typed_config(
    schema: type, values: dict[str, Any], path: tuple[str | int, ...]
) -> Any:
    fields = validate_native(schema, values, path)
    for name, (kind, annotation) in classify_fields(schema).items():
        if kind == "native" or name not in values:
            continue
        fields[name] = _materialize(values[name], (*path, name))
        if kind == "object":
            check_object(fields[name], annotation, values[name], (*path, name), schema)
    return schema(**fields)


def _materialize(node: Any, path: tuple[str | int, ...]) -> Any:
    if isinstance(node, (dict, DictConfig)):
        node = {k: v for k, v in node.items() if k != META_KEY}
        if CLASS_KEY in node:
            return _build(node, path=path)
        if REF_KEY in node:
            if len(node) > 1:
                raise ValueError(
                    f"Invalid config node with `{REF_KEY}` key: {node}. A node using "
                    f"`{REF_KEY}` cannot contain any other keys."
                )
            return import_object(node[REF_KEY])
        for key in node:
            if isinstance(key, str) and key.startswith("$"):
                raise ValueError(
                    f"Invalid config node: {node}. Key `{key}` is not supported here; "
                    "keys starting with `$` are reserved."
                )
        return {k: _materialize(v, (*path, k)) for k, v in node.items()}
    if isinstance(node, (list, ListConfig)):
        return [_materialize(v, (*path, index)) for index, v in enumerate(node)]
    return node
