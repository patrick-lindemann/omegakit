import dataclasses
import functools
from collections.abc import Callable
from typing import Any, get_origin, is_typeddict, overload

from omegaconf import DictConfig

from .config import cast_config
from .errors import ConfigSchemaError, ConfigTargetError
from .features import ARGS_KEY, TARGET_KEY
from .typecheck import Call, Container, check, read_fields, union_members
from .utils.describe import describe_node, get_full_key


@overload
def instantiate[T](config: DictConfig | dict[str, Any], schema: type[T]) -> T: ...


@overload
def instantiate(config: DictConfig | dict[str, Any], schema: None = None) -> Any: ...


def instantiate(config: DictConfig | dict[str, Any], schema: type | None = None) -> Any:
    return _instantiate(config, schema, is_partial=False)


@overload
def prepare[T](
    config: DictConfig | dict[str, Any], schema: type[T]
) -> functools.partial[T]: ...


@overload
def prepare(
    config: DictConfig | dict[str, Any], schema: None = None
) -> functools.partial[Any]: ...


def prepare(
    config: DictConfig | dict[str, Any], schema: type | None = None
) -> functools.partial[Any]:
    return _instantiate(config, schema, is_partial=True)


def make_node(
    target: Callable[..., Any], /, *args: Any, **kwargs: Any
) -> dict[str, Any]:
    # A callable object, such as a `functools.partial`, has no name of its own
    qualname = getattr(target, "__qualname__", None)
    if qualname is None or "." in qualname:
        raise ConfigTargetError(
            f"Cannot create a node for `{qualname or target!r}`: only objects "
            "defined at module level can be imported by their path."
        )
    node = {TARGET_KEY: f"{target.__module__}.{qualname}", **kwargs}
    if args:
        node[ARGS_KEY] = list(args)
    return node


def _instantiate(
    config: DictConfig | dict[str, Any], schema: type | None, is_partial: bool
) -> Any:
    config = cast_config(config)
    # Checked before the first call, so that nothing is called for an invalid config
    call = check(config, schema, is_deferred=is_partial)
    if not isinstance(call, Call):
        raise ConfigTargetError(
            f"There is nothing to instantiate: {describe_node(config)} has no "
            f"`{TARGET_KEY}`."
        )
    if is_partial:
        if schema is not None and not isinstance(call.target, type):
            raise ConfigSchemaError(
                f"`{call.name}` is a function, and the result of a partial cannot be "
                f"checked to be a `{schema.__qualname__}`."
            )
        return _build(dataclasses.replace(call, is_partial=True))
    # Also for a class, whose `from_config` may return anything
    typed_call = (
        call if schema is None else dataclasses.replace(call, result_annotation=schema)
    )
    return _build(typed_call)


def _build(value: Any) -> Any:
    if isinstance(value, Container):
        if isinstance(value.items, dict):
            return {key: _build(item) for key, item in value.items.items()}
        return type(value.items)(_build(item) for item in value.items)
    if not isinstance(value, Call):
        return value
    positional_arguments = [_build(argument) for argument in value.positional_arguments]
    arguments = {key: _build(argument) for key, argument in value.arguments.items()}
    try:
        if not hasattr(value.target, "from_config"):
            if value.is_partial:
                return functools.partial(
                    value.target, *positional_arguments, **arguments
                )
            instance = value.target(*positional_arguments, **arguments)
        elif not value.is_partial:
            instance = value.target.from_config(arguments)
        elif value.schema is None or value.schema is value.target:
            return functools.partial(value.target.from_config, arguments)
        else:
            return functools.partial(_call_from_config, value, value.schema, arguments)
    except Exception as error:
        error.add_note(f"  while calling `{value.name}` at {describe_node(value.node)}")
        raise
    members = union_members(value.result_annotation)
    classes = tuple(
        get_origin(member) or member for member in members if not is_typeddict(member)
    )
    try:
        is_valid = value.result_annotation is Any or isinstance(instance, classes)
    # Not every annotation can be checked, as where the config is checked
    except TypeError:
        return instance
    if not is_valid:
        annotation = value.result_annotation
        expected = (
            annotation.__qualname__ if isinstance(annotation, type) else annotation
        )
        raise ConfigSchemaError(
            f"Expected `{expected}`, but `{value.name}` returned `{instance!r}`.",
            get_full_key(value.node),
        )
    return instance


def _call_from_config(
    call: Call, schema: type, arguments: dict[Any, Any], **kwargs: Any
) -> Any:
    fields = read_fields(schema)
    # What the call gives for a key of the schema completes the checked values
    values = arguments | {key: kwargs[key] for key in kwargs if key in fields}
    other_kwargs = {key: kwargs[key] for key in kwargs if key not in fields}
    missing_keys = [
        key for key, field in fields.items() if field.is_required and key not in values
    ]
    if missing_keys:
        raise ConfigSchemaError(
            f"`{schema.__qualname__}` requires "
            f"{', '.join(f'`{key}`' for key in missing_keys)}.",
            get_full_key(call.node),
        )
    return call.target.from_config(values, **other_kwargs)
