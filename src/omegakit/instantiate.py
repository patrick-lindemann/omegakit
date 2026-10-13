import dataclasses
import functools
from typing import Any, get_origin, is_typeddict, overload

from omegaconf import DictConfig

from ._features.target import TARGET_KEY, TargetSyntaxError
from ._utils.describe import describe_node
from .schema import SchemaTypeError, split_union
from .validate import Call, Items, check


@overload
def instantiate[T](config: DictConfig, schema: type[T]) -> T: ...


@overload
def instantiate(config: DictConfig, schema: None = None) -> Any: ...


def instantiate(config: DictConfig, schema: type | None = None) -> Any:
    return _instantiate(config, schema, is_partial=False)


@overload
def prepare[T](config: DictConfig, schema: type[T]) -> functools.partial[T]: ...


@overload
def prepare(config: DictConfig, schema: None = None) -> functools.partial[Any]: ...


def prepare(config: DictConfig, schema: type | None = None) -> functools.partial[Any]:
    return _instantiate(config, schema, is_partial=True)


def _instantiate(config: DictConfig, schema: type | None, is_partial: bool) -> Any:
    # Checked before the first call, so that nothing is called for an invalid config
    call = check(config, schema)
    if not isinstance(call, Call):
        raise TargetSyntaxError(
            f"There is nothing to instantiate: {describe_node(config)} has no "
            f"`{TARGET_KEY}`."
        )
    if is_partial:
        return _build(dataclasses.replace(call, is_partial=True))
    # Also for a class, whose `from_config` may return anything
    typed_call = (
        call if schema is None else dataclasses.replace(call, result_annotation=schema)
    )
    return _build(typed_call)


def _build(value: Any) -> Any:
    if isinstance(value, Items):
        if isinstance(value.items, dict):
            return {key: _build(item) for key, item in value.items.items()}
        return type(value.items)(_build(item) for item in value.items)
    if not isinstance(value, Call):
        return value
    arguments = {key: _build(argument) for key, argument in value.arguments.items()}
    try:
        if hasattr(value.target, "from_config"):
            if value.is_partial:
                return functools.partial(value.target.from_config, arguments)
            instance = value.target.from_config(arguments)
        elif value.is_partial:
            return functools.partial(value.target, **arguments)
        else:
            instance = value.target(**arguments)
    except Exception as error:
        error.add_note(f"  while calling `{value.name}` at {describe_node(value.node)}")
        raise
    members = split_union(value.result_annotation)
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
        type_error = SchemaTypeError(
            f"Expected `{expected}`, but `{value.name}` returned `{instance!r}`."
        )
        type_error.add_note(f"  at {describe_node(value.node)}")
        raise type_error
    return instance
