import dataclasses
import functools
from typing import Any, NamedTuple, get_origin

from omegaconf import DictConfig, ListConfig, TupleConfig
from omegaconf.errors import InterpolationResolutionError, MissingMandatoryValue

from ._core.error import OmegaKitBaseException
from ._features.class_ import CLASS_KEY, import_class, read_arguments
from ._features.meta import META_KEY
from ._features.ref import REF_KEY, import_ref
from ._utils.describe import describe_error, describe_node
from .schema import (
    SchemaDefinitionError,
    SchemaKeyError,
    SchemaMissingValueError,
    SchemaTypeError,
    convert_data,
    find_item_annotation,
    find_schema,
    find_section,
    read_fields,
    split_union,
)


class ConfigValidationError(OmegaKitBaseException):
    pass


class ValidationSyntaxError(ConfigValidationError, ValueError):
    pass


class ValidationInterpolationError(ConfigValidationError, InterpolationResolutionError):
    pass


class ValidationMissingValueError(ConfigValidationError, MissingMandatoryValue):
    pass


class ValidationCycleError(ConfigValidationError):
    pass


class Call(NamedTuple):
    node: DictConfig
    name: str
    target: Any
    schema: type | None
    is_partial: bool
    arguments: dict[Any, Any]


# A mapping, list or tuple of the config, unlike a `dict` or `list` that is a value
class Items(NamedTuple):
    items: dict[Any, Any] | list[Any] | tuple[Any, ...]


def validate(
    config: DictConfig | ListConfig | TupleConfig, schema: type | None = None
) -> None:
    check(config, schema)


def check(
    config: DictConfig | ListConfig | TupleConfig, schema: type | None = None
) -> Any:
    # The root is not read through a parent, which is where a `???` raises
    if config._is_missing():
        raise ValidationMissingValueError("The config is `???`.")
    if schema is not None and not isinstance(schema, type):
        raise SchemaDefinitionError(f"`schema` must be a class, not `{schema!r}`.")
    annotation = Any if schema is None else schema
    checked_config = _check_node(config, [], annotation)
    try:
        _check_type(checked_config, annotation)
    except SchemaTypeError as error:
        error.add_note(f"  at {describe_node(config)}")
        raise
    return checked_config


def _check_node(
    node: DictConfig | ListConfig | TupleConfig,
    active_nodes: list[DictConfig | ListConfig | TupleConfig],
    annotation: Any,
) -> Any:
    is_active = [active_node is node for active_node in active_nodes]
    if any(is_active):
        cycle_nodes = [*active_nodes[is_active.index(True) :], node]
        cycle = " -> ".join(describe_node(item) for item in cycle_nodes)
        raise ValidationCycleError(f"The config contains itself: {cycle}.")
    active_nodes = [*active_nodes, node]
    containers = (dict,) if isinstance(node, DictConfig) else (list,)
    item_annotation = find_item_annotation(annotation, containers) or Any
    if not isinstance(node, DictConfig):
        items = [
            _check_value(node, index, active_nodes, item_annotation)
            for index in range(len(node))
        ]
        return Items(items if isinstance(node, ListConfig) else tuple(items))
    if CLASS_KEY in node.keys():  # noqa: SIM118
        return _check_call(node, active_nodes)
    try:
        if REF_KEY in node.keys():  # noqa: SIM118
            return import_ref(node)
        keys = [key for key in node.keys() if key != META_KEY]  # noqa: SIM118
        reserved_keys = [key for key in keys if str(key).startswith("$")]
        if reserved_keys:
            raise ValidationSyntaxError(
                f"{', '.join(f'`{key}`' for key in reserved_keys)} cannot stand "
                "here: keys that start with `$` are reserved."
            )
        section = find_section(annotation)
        schema = find_schema(section)
    except OmegaKitBaseException as error:
        error.add_note(f"  at {describe_node(node)}")
        raise
    if section is None or schema is None:
        items = {
            key: _check_value(node, key, active_nodes, item_annotation) for key in keys
        }
        return Items(items)
    name = f"{section.__module__}.{section.__qualname__}"
    arguments = _check_schema(node, schema, keys, active_nodes)
    return Call(node, name, section, schema, False, arguments)


def _check_call(
    node: DictConfig, active_nodes: list[DictConfig | ListConfig | TupleConfig]
) -> Call:
    try:
        is_partial, keys = read_arguments(node)
        target = import_class(node)
        name = node[CLASS_KEY]
        schema = find_schema(target)
    except OmegaKitBaseException as error:
        error.add_note(f"  at {describe_node(node)}")
        raise
    if schema is None:
        arguments = {key: _check_value(node, key, active_nodes, Any) for key in keys}
    else:
        arguments = _check_schema(node, schema, keys, active_nodes)
    return Call(node, name, target, schema, is_partial, arguments)


def _check_schema(
    node: DictConfig,
    schema: type,
    keys: list[Any],
    active_nodes: list[DictConfig | ListConfig | TupleConfig],
) -> dict[Any, Any]:
    try:
        fields = read_fields(schema)
        unknown_keys = [key for key in keys if key not in fields]
        if unknown_keys:
            raise SchemaKeyError(
                f"{', '.join(f'`{key}`' for key in unknown_keys)} is not a field of "
                f"`{schema.__qualname__}`."
            )
        missing_keys = [
            key
            for key, field in fields.items()
            if field.is_required and key not in keys
        ]
        if missing_keys:
            raise SchemaMissingValueError(
                f"`{schema.__qualname__}` requires "
                f"{', '.join(f'`{key}`' for key in missing_keys)}."
            )
    except OmegaKitBaseException as error:
        error.add_note(f"  at {describe_node(node)}")
        raise
    arguments = {}
    for key in keys:
        annotation = Any if fields[key].is_data else fields[key].annotation
        arguments[key] = _check_value(node, key, active_nodes, annotation)
    try:
        data_values = {
            key: _unwrap_data(value)
            for key, value in arguments.items()
            if fields[key].is_data
        }
        converted_values = convert_data(schema, data_values)
    except OmegaKitBaseException as error:
        error.add_note(f"  at {describe_node(node)}")
        raise
    return arguments | converted_values


def _check_value(
    parent: DictConfig | ListConfig | TupleConfig,
    key: Any,
    active_nodes: list[DictConfig | ListConfig | TupleConfig],
    annotation: Any,
) -> Any:
    try:
        value = parent[key]
    except MissingMandatoryValue as error:
        missing_error = ValidationMissingValueError("The value is `???`.")
        missing_error.add_note(f"  at `{parent._get_full_key(key)}`")
        raise missing_error from error
    except InterpolationResolutionError as error:
        interpolation_error = ValidationInterpolationError(
            f"Cannot resolve the value: {describe_error(error)}"
        )
        interpolation_error.add_note(f"  at `{parent._get_full_key(key)}`")
        raise interpolation_error from error
    if isinstance(value, (DictConfig, ListConfig, TupleConfig)):
        value = _check_node(value, active_nodes, annotation)
    try:
        _check_type(value, annotation)
    except SchemaTypeError as error:
        error.add_note(f"  at `{parent._get_full_key(key)}`")
        raise
    return value


def _unwrap_data(value: Any) -> Any:
    if isinstance(value, Call):
        raise SchemaTypeError(
            f"`{CLASS_KEY}: {value.name}` cannot stand in a field that holds plain "
            "values."
        )
    if not isinstance(value, Items):
        return value
    if isinstance(value.items, dict):
        return {key: _unwrap_data(item) for key, item in value.items.items()}
    return type(value.items)(_unwrap_data(item) for item in value.items)


def _check_type(value: Any, annotation: Any) -> None:
    if annotation is Any:
        return
    # A parametrized class, such as `list[X]`, is checked as the class alone
    classes = tuple(get_origin(member) or member for member in split_union(annotation))
    try:
        if not isinstance(value, Call):
            given_value = value.items if isinstance(value, Items) else value
            is_valid = isinstance(given_value, classes)
        elif value.is_partial:
            is_valid = issubclass(functools.partial, classes)
        else:
            # A class also fits a field that is annotated with its schema
            schemas: tuple[Any, ...] = tuple(
                item for item in classes if dataclasses.is_dataclass(item)
            )
            is_valid = issubclass(value.target, classes) or (
                value.schema is not None and issubclass(value.schema, schemas)
            )
    # Not every annotation and target can be checked, such as a `Literal`, a
    # `Protocol` that is not runtime-checkable, and a function as the target
    except TypeError:
        return
    if is_valid:
        return
    if isinstance(value, Call) and value.is_partial:
        given = f"a partial of `{value.name}`"
    elif isinstance(value, Call):
        given = f"`{CLASS_KEY}: {value.name}`"
    elif isinstance(value, Items) and isinstance(value.items, dict):
        given = "a mapping"
    elif isinstance(value, Items):
        given = f"a {type(value.items).__name__}"
    else:
        given = f"`{value!r}`"
    expected = annotation.__qualname__ if isinstance(annotation, type) else annotation
    raise SchemaTypeError(f"Expected `{expected}`, but the config gives {given}.")
