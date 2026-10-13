import functools
from typing import Any, overload

from omegaconf import DictConfig

from ._features.class_ import CLASS_KEY, ClassSyntaxError
from ._utils.describe import describe_node
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
        raise ClassSyntaxError(
            f"There is nothing to instantiate: {describe_node(config)} has no "
            f"`{CLASS_KEY}`."
        )
    if is_partial:
        call = call._replace(is_partial=True)
    return _build(call)


def _build(value: Any) -> Any:
    if isinstance(value, Items):
        if isinstance(value.items, dict):
            return {key: _build(item) for key, item in value.items.items()}
        return type(value.items)(_build(item) for item in value.items)
    if not isinstance(value, Call):
        return value
    node, name, target, schema, is_partial, checked_arguments = value
    arguments: Any = {
        key: _build(argument) for key, argument in checked_arguments.items()
    }
    try:
        # A `Configurable` gets its arguments as an instance of its schema
        if schema is not None and schema is not target:
            arguments = schema(**arguments)
        if hasattr(target, "from_config"):
            if is_partial:
                instance = functools.partial(target.from_config, arguments)
            else:
                instance = target.from_config(arguments)
        elif is_partial:
            instance = functools.partial(target, **arguments)
        else:
            instance = target(**arguments)
    except Exception as error:
        error.add_note(f"  while calling `{name}` at {describe_node(node)}")
        raise
    return instance
