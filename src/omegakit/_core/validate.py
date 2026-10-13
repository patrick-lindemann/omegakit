import dataclasses
import functools
import types
from typing import Any, get_args, get_origin, is_typeddict

from omegaconf import DictConfig, ListConfig, OmegaConf, TupleConfig
from omegaconf.errors import InterpolationResolutionError, MissingMandatoryValue

from .config import Config, cast_config
from .errors import (
    ConfigSchemaError,
    ConfigTargetError,
    ConfigValidationError,
    OmegaKitBaseException,
    SchemaDefinitionError,
    ValidationInterpolationError,
    ValidationMissingValueError,
)
from .features.meta import META_KEY
from .features.symbol import SYMBOL_KEY, import_symbol
from .features.target import ARGS_KEY, TARGET_KEY, import_target, read_arguments
from .schema import (
    convert_data,
    convert_item,
    find_item_annotation,
    find_key_annotation,
    find_schema,
    find_section,
    find_tuple_annotations,
    is_data,
    read_fields,
    read_positions,
    split_union,
)
from .utils.describe import describe_error, describe_node, get_full_key


@dataclasses.dataclass(frozen=True)
class Call:
    node: DictConfig
    name: str
    target: Any
    schema: type | None
    is_partial: bool
    arguments: dict[Any, Any]
    result_annotation: Any = Any
    positional_arguments: list[Any] | tuple[Any, ...] = ()


# A mapping, list or tuple of the config, unlike a `dict` or `list` that is a value
@dataclasses.dataclass(frozen=True)
class Items:
    items: dict[Any, Any] | list[Any] | tuple[Any, ...]


def validate(
    config: Config | dict[Any, Any] | list[Any] | tuple[Any, ...],
    schema: type | None = None,
) -> None:
    check(cast_config(config), schema)


def check(
    config: Config,
    schema: type | None = None,
    is_deferred: bool = False,
) -> Any:
    # The root is not read through a parent, which is where a `???` raises
    if config._is_missing():
        raise ValidationMissingValueError("The config is `???`.")
    if schema is not None and not isinstance(schema, type):
        raise SchemaDefinitionError(f"`schema` must be a class, not `{schema!r}`.")
    annotation = Any if schema is None else schema
    checked_config = _check_node(config, [], annotation, is_deferred)
    try:
        typed_config = _check_type(checked_config, annotation)
    except ConfigSchemaError as error:
        if error.full_key is None:
            error.full_key = get_full_key(config)
        raise
    return typed_config


def _check_node(
    node: Config,
    active_nodes: list[Config],
    annotation: Any,
    is_deferred: bool = False,
) -> Any:
    is_active = [active_node is node for active_node in active_nodes]
    if any(is_active):
        cycle_nodes = [*active_nodes[is_active.index(True) :], node]
        cycle = " -> ".join(describe_node(item) for item in cycle_nodes)
        raise ConfigValidationError(f"The config contains itself: {cycle}.")
    active_nodes = [*active_nodes, node]
    containers = (dict,) if isinstance(node, DictConfig) else (list,)
    item_annotation = find_item_annotation(annotation, containers) or Any
    if not isinstance(node, DictConfig):
        return _check_items(node, active_nodes, annotation, item_annotation)
    if TARGET_KEY in node.keys():  # noqa: SIM118
        return _check_call(node, active_nodes, is_deferred)
    try:
        if SYMBOL_KEY in node.keys():  # noqa: SIM118
            value = import_symbol(node)
            symbol_section = find_section(annotation)
            if symbol_section is None or not isinstance(value, dict):
                return value
            # An existing `dict` is checked like a mapping that the config gives
            mapping = OmegaConf.create(value, flags={"allow_objects": True})
            symbol_keys = list(mapping.keys())
            symbol_arguments = _check_schema(
                mapping, symbol_section, symbol_keys, active_nodes, False
            )
            return Items(symbol_arguments)
        keys = [key for key in node.keys() if key != META_KEY]  # noqa: SIM118
        reserved_keys = [key for key in keys if str(key).startswith("$")]
        if reserved_keys:
            raise ConfigValidationError(
                f"{', '.join(f'`{key}`' for key in reserved_keys)} cannot stand "
                "here: keys that start with `$` are reserved."
            )
        section = find_section(annotation)
        # The keys of a dictionary of mappings or objects, which OmegaConf does not see
        key_annotation = find_key_annotation(annotation)
        wrong_keys = [
            key
            for key in keys
            if key_annotation is not Any and not isinstance(key, key_annotation)
        ]
        if wrong_keys:
            raise ConfigSchemaError(
                f"{', '.join(f'`{key!r}`' for key in wrong_keys)} is not a "
                f"`{key_annotation.__name__}`, as the keys of `{annotation}` are."
            )
    except OmegaKitBaseException as error:
        # A mapping behind `$symbol` is not part of the config, so its keys name nothing
        error.full_key = get_full_key(node)
        raise
    # A module can raise anything while it is imported
    except Exception as error:
        error.add_note(f"  at {describe_node(node)}")
        raise
    if section is None:
        items = {
            key: _check_value(node, key, active_nodes, item_annotation) for key in keys
        }
        return Items(items)
    # A mapping that is checked against a schema stays a mapping
    arguments = _check_schema(node, section, keys, active_nodes, False)
    return Items(arguments)


def _check_items(
    node: ListConfig | TupleConfig,
    active_nodes: list[Config],
    annotation: Any,
    item_annotation: Any,
) -> Items:
    item_annotations = find_tuple_annotations(annotation, len(node))
    is_tuple = item_annotations is not None or not isinstance(node, ListConfig)
    if item_annotations is None:
        item_annotations = [item_annotation] * len(node)
    if len(item_annotations) != len(node):
        raise ConfigSchemaError(
            f"Expected {len(item_annotations)} items, but the config gives "
            f"{len(node)}.",
            get_full_key(node),
        )
    items = []
    for index, position_annotation in enumerate(item_annotations):
        if not (is_tuple and is_data(position_annotation)):
            item = _check_value(node, index, active_nodes, position_annotation)
            items.append(item)
            continue
        # A plain position of a tuple is converted like a plain field
        item = _check_value(node, index, active_nodes, Any)
        try:
            converted_item = convert_item(position_annotation, _unwrap_data(item))
        except OmegaKitBaseException as error:
            if error.full_key is None:
                error.full_key = node._get_full_key(index)
            raise
        items.append(converted_item)
    return Items(tuple(items) if is_tuple else items)


def _check_call(
    node: DictConfig,
    active_nodes: list[Config],
    is_deferred: bool,
) -> Call:
    try:
        target_arguments = read_arguments(node)
        target = import_target(node)
        name = node[TARGET_KEY]
        if is_typeddict(target):
            raise ConfigSchemaError(
                f"`{TARGET_KEY}: {name}` names a schema, and nothing is built from one."
            )
        schema = find_schema(target)
        if target_arguments.has_args and hasattr(target, "from_config"):
            raise ConfigTargetError(
                f"`{name}` takes its arguments by name, so it cannot take `{ARGS_KEY}`."
            )
    except OmegaKitBaseException as error:
        if error.full_key is None:
            error.full_key = get_full_key(node)
        raise
    # A module can raise anything while it is imported
    except Exception as error:
        error.add_note(f"  at {describe_node(node)}")
        raise
    positional_arguments: list[Any] | tuple[Any, ...] = ()
    positional_keys: list[str] = []
    if target_arguments.has_args:
        args = _read_value(node, ARGS_KEY)
        args_annotation: Any = Any
        try:
            if not isinstance(args, (ListConfig, TupleConfig)):
                raise ConfigTargetError(f"`{ARGS_KEY}` must be a list, not `{args!r}`.")
            if schema is not None:
                # A dataclass binds the items to its fields, as its constructor does
                fields = read_fields(schema)
                positions = read_positions(schema)
                if len(args) > len(positions):
                    raise ConfigSchemaError(
                        f"`{schema.__qualname__}` takes {len(positions)} positional "
                        f"arguments, but `{ARGS_KEY}` gives {len(args)}."
                    )
                positional_keys = positions[: len(args)]
                # A parameter that is no field, such as an `InitVar`, is not checked
                item_annotations = tuple(
                    fields[key].annotation if key in fields else Any
                    for key in positional_keys
                )
                args_annotation = types.GenericAlias(tuple, item_annotations)
        except OmegaKitBaseException as error:
            if error.full_key is None:
                error.full_key = get_full_key(node)
            raise
        checked_args = _check_node(args, active_nodes, args_annotation)
        positional_arguments = checked_args.items
    if schema is None:
        arguments = {
            key: _check_value(node, key, active_nodes, Any)
            for key in target_arguments.keys
        }
    else:
        # A partial may leave required keys open until it is called
        is_open = target_arguments.is_partial or is_deferred
        arguments = _check_schema(
            node, schema, target_arguments.keys, active_nodes, is_open, positional_keys
        )
    return Call(
        node,
        name,
        target,
        schema,
        target_arguments.is_partial,
        arguments,
        positional_arguments=positional_arguments,
    )


def _check_schema(
    node: DictConfig,
    schema: type,
    keys: list[Any],
    active_nodes: list[Config],
    is_open: bool,
    positional_keys: list[str] | tuple[str, ...] = (),
) -> dict[Any, Any]:
    try:
        fields = read_fields(schema)
        unknown_keys = [key for key in keys if key not in fields]
        if unknown_keys:
            raise ConfigSchemaError(
                f"{', '.join(f'`{key}`' for key in unknown_keys)} is not a field of "
                f"`{schema.__qualname__}`."
            )
        repeated_keys = [key for key in keys if key in positional_keys]
        if repeated_keys:
            raise ConfigSchemaError(
                f"{', '.join(f'`{key}`' for key in repeated_keys)} is given twice, by "
                f"`{ARGS_KEY}` and by name."
            )
        missing_keys = [
            key
            for key, field in fields.items()
            if field.is_required and key not in keys and key not in positional_keys
        ]
        if missing_keys and not is_open:
            raise ConfigSchemaError(
                f"`{schema.__qualname__}` requires "
                f"{', '.join(f'`{key}`' for key in missing_keys)}."
            )
    except OmegaKitBaseException as error:
        if error.full_key is None:
            error.full_key = get_full_key(node)
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
        if error.full_key is None:
            error.full_key = get_full_key(node)
        raise
    return arguments | converted_values


def _check_value(
    parent: Config,
    key: Any,
    active_nodes: list[Config],
    annotation: Any,
) -> Any:
    value = _read_value(parent, key)
    if isinstance(value, (DictConfig, ListConfig, TupleConfig)):
        value = _check_node(value, active_nodes, annotation)
    try:
        typed_value = _check_type(value, annotation)
    except ConfigSchemaError as error:
        if error.full_key is None:
            error.full_key = parent._get_full_key(key)
        raise
    return typed_value


def _read_value(parent: Config, key: Any) -> Any:
    try:
        return parent[key]
    except MissingMandatoryValue as error:
        raise ValidationMissingValueError(
            "The value is `???`.", parent._get_full_key(key)
        ) from error
    except InterpolationResolutionError as error:
        raise ValidationInterpolationError(
            f"Cannot resolve the value: {describe_error(error)}",
            parent._get_full_key(key),
        ) from error


def _unwrap_data(value: Any) -> Any:
    if isinstance(value, Call):
        raise ConfigSchemaError(
            f"`{TARGET_KEY}: {value.name}` cannot stand in a field that holds plain "
            "values."
        )
    if not isinstance(value, Items):
        return value
    if isinstance(value.items, dict):
        return {key: _unwrap_data(item) for key, item in value.items.items()}
    return type(value.items)(_unwrap_data(item) for item in value.items)


def _check_type(value: Any, annotation: Any) -> Any:
    if annotation is Any:
        return value
    members = split_union(annotation)
    # A field that is annotated with a schema takes a mapping of the config
    if any(is_typeddict(member) for member in members):
        if isinstance(value, Items) and isinstance(value.items, dict):
            return value
        members = tuple(member for member in members if not is_typeddict(member))
    # A parametrized class, such as `list[X]`, is checked as the class alone
    classes = tuple(get_origin(member) or member for member in members)
    # `type[X]` takes a subclass of `X`
    bounds = tuple(
        get_args(member)[0]
        for member in members
        if get_origin(member) is type and get_args(member)[0] is not Any
    )
    try:
        if not classes:
            is_valid = False
        elif not isinstance(value, Call):
            given_value = value.items if isinstance(value, Items) else value
            is_valid = isinstance(given_value, classes)
            if is_valid and bounds and isinstance(given_value, type):
                is_valid = issubclass(given_value, bounds)
        elif value.is_partial:
            is_valid = issubclass(functools.partial, classes)
        elif not isinstance(value.target, type):
            # The result of a function is known only when it returns
            return dataclasses.replace(value, result_annotation=annotation)
        else:
            is_valid = issubclass(value.target, classes)
    # Not every annotation can be checked, such as a `Literal` or a `Protocol` that
    # is not runtime-checkable
    except TypeError:
        return value
    if is_valid:
        return value
    if isinstance(value, Call) and value.is_partial:
        given = f"a partial of `{value.name}`"
    elif isinstance(value, Call):
        given = f"`{TARGET_KEY}: {value.name}`"
    elif isinstance(value, Items) and isinstance(value.items, dict):
        given = "a mapping"
    elif isinstance(value, Items):
        given = f"a {type(value.items).__name__}"
    else:
        given = f"`{value!r}`"
    expected = annotation.__qualname__ if isinstance(annotation, type) else annotation
    raise ConfigSchemaError(f"Expected `{expected}`, but the config gives {given}.")
