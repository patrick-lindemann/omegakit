import dataclasses
import functools
import types
from dataclasses import dataclass
from typing import Any, Literal, get_args, get_origin

from omegaconf import DictConfig, ListConfig, OmegaConf, TupleConfig
from typing_extensions import is_typeddict

from omegakit._core.config import Config
from omegakit._core.errors import (
    ConfigSchemaError,
    ConfigTargetError,
    ConfigValidationError,
    OmegaKitBaseException,
    SchemaDefinitionError,
    ValidationMissingValueError,
)
from omegakit._core.features import (
    ARGS_KEY,
    META_KEY,
    SYMBOL_KEY,
    TARGET_KEY,
    import_symbol,
    import_target,
    read_arguments,
)
from omegakit._core.utils.describe import describe_node, get_full_key
from omegakit._core.utils.notes import add_note
from omegakit._core.utils.read import MISSING_VALUE, read_value

from .annotations import (
    find_item_annotation,
    find_position_annotations,
    find_typed_dicts,
    is_plain_value,
    union_members,
)
from .convert import convert_keys, convert_plain_values, convert_value
from .fields import find_schema, read_fields, read_positional_names


@dataclass(frozen=True)
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
@dataclass(frozen=True)
class Container:
    items: dict[Any, Any] | list[Any] | tuple[Any, ...]


def check(
    config: Config,
    schema: type | None = None,
    is_deferred: bool = False,
    allow_missing: bool = False,
) -> Any:
    # The root is not read through a parent, which is where a `???` raises
    if config._is_missing():
        if allow_missing:
            return MISSING_VALUE
        raise ValidationMissingValueError("The config is `???`.")
    if schema is not None and not isinstance(schema, type):
        raise SchemaDefinitionError(f"`schema` must be a class, not `{schema!r}`.")
    annotation = Any if schema is None else schema
    checked_config = _check_node(config, [], allow_missing, annotation, is_deferred)
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
    allow_missing: bool,
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
    try:
        container_item_annotation = find_item_annotation(annotation, containers)
    except OmegaKitBaseException as error:
        if error.full_key is None:
            error.full_key = get_full_key(node)
        raise
    item_annotation = container_item_annotation or Any
    if not isinstance(node, DictConfig):
        return _check_items(
            node, active_nodes, allow_missing, annotation, item_annotation
        )
    if TARGET_KEY in node.keys():  # noqa: SIM118
        return _check_call(node, active_nodes, allow_missing, is_deferred)
    if SYMBOL_KEY in node.keys():  # noqa: SIM118
        return _check_symbol(node, active_nodes, allow_missing, annotation)
    try:
        keys = [key for key in node.keys() if key != META_KEY]  # noqa: SIM118
        reserved_keys = [key for key in keys if str(key).startswith("$")]
        if reserved_keys:
            raise ConfigValidationError(
                f"{', '.join(f'`{key}`' for key in reserved_keys)} cannot stand "
                "here: keys that start with `$` are reserved."
            )
        sections = find_typed_dicts(annotation)
        # A union such as `ModelConfig | dict[str, Model]` has a `dict` to fall back to
        has_dict = container_item_annotation is not None
        section = (
            _select_section(node, sections, keys, allow_missing, has_dict)
            if sections
            else None
        )
        # The keys of a dictionary of mappings or objects, which OmegaConf does not see
        converted_keys = convert_keys(annotation, keys)
    except OmegaKitBaseException as error:
        if error.full_key is None:
            error.full_key = get_full_key(node)
        raise
    if section is None:
        items = {
            converted_key: _check_value(
                node, key, active_nodes, allow_missing, item_annotation
            )
            for key, converted_key in zip(keys, converted_keys, strict=True)
        }
        return Container(items)
    # A mapping that is checked against a schema stays a mapping
    arguments = _check_schema(node, section, keys, active_nodes, allow_missing, False)
    return Container(arguments)


def _check_items(
    node: ListConfig | TupleConfig,
    active_nodes: list[Config],
    allow_missing: bool,
    annotation: Any,
    item_annotation: Any,
) -> Container:
    try:
        item_annotations = find_position_annotations(annotation, len(node))
    except OmegaKitBaseException as error:
        if error.full_key is None:
            error.full_key = get_full_key(node)
        raise
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
        if not (is_tuple and is_plain_value(position_annotation)):
            item = _check_value(
                node, index, active_nodes, allow_missing, position_annotation
            )
            items.append(item)
            continue
        # A plain position of a tuple is converted like a plain field
        item = _check_value(node, index, active_nodes, allow_missing, Any)
        try:
            plain_item = _unwrap_plain_value(item)
            # OmegaConf converts no tuple that holds `???`, so a missing value or one
            # that holds a missing item stays as it is
            if allow_missing and _holds_missing_value(plain_item):
                converted_item = plain_item
            else:
                converted_item = convert_value(position_annotation, plain_item)
        except OmegaKitBaseException as error:
            if error.full_key is None:
                error.full_key = node._get_full_key(index)
            raise
        items.append(converted_item)
    return Container(tuple(items) if is_tuple else items)


def _check_call(
    node: DictConfig,
    active_nodes: list[Config],
    allow_missing: bool,
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
        add_note(error, f"  at {describe_node(node)}")
        raise
    positional_arguments: list[Any] | tuple[Any, ...] = ()
    positional_keys: list[str] = []
    if target_arguments.has_args:
        args = read_value(node, ARGS_KEY)
        args_annotation: Any = Any
        try:
            if not isinstance(args, (ListConfig, TupleConfig)):
                raise ConfigTargetError(f"`{ARGS_KEY}` must be a list, not `{args!r}`.")
            if schema is not None:
                # A dataclass binds the items to its fields, as its constructor does
                fields = read_fields(schema)
                positions = read_positional_names(schema)
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
        checked_args = _check_node(args, active_nodes, allow_missing, args_annotation)
        positional_arguments = checked_args.items
    if schema is None:
        arguments = {
            key: _check_value(node, key, active_nodes, allow_missing, Any)
            for key in target_arguments.keys
        }
    else:
        # A partial may leave required keys open until it is called
        is_open = target_arguments.is_partial or is_deferred
        arguments = _check_schema(
            node,
            schema,
            target_arguments.keys,
            active_nodes,
            allow_missing,
            is_open,
            positional_keys,
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


def _check_symbol(
    node: DictConfig, active_nodes: list[Config], allow_missing: bool, annotation: Any
) -> Any:
    try:
        value = import_symbol(node)
        sections = find_typed_dicts(annotation)
        if not sections or not isinstance(value, dict):
            return value
        # An existing `dict` is checked like a mapping that the config gives
        mapping = OmegaConf.create(value, flags={"allow_objects": True})
        keys = list(mapping.keys())
        section = _select_section(mapping, sections, keys, allow_missing)
        if section is None:
            return value
        arguments = _check_schema(
            mapping, section, keys, active_nodes, allow_missing, False
        )
    except OmegaKitBaseException as error:
        # A mapping behind `$symbol` is not part of the config, so its keys name nothing
        error.full_key = get_full_key(node)
        raise
    # A module can raise anything while it is imported
    except Exception as error:
        add_note(error, f"  at {describe_node(node)}")
        raise
    return Container(arguments)


def _select_section(
    node: DictConfig,
    sections: tuple[type, ...],
    keys: list[Any],
    allow_missing: bool,
    has_dict: bool = False,
) -> type | None:
    if len(sections) == 1 and not has_dict:
        return sections[0]
    # A mapping is checked against the first schema of a union that it fits
    mismatches = []
    for section in sections:
        mismatch = _find_mismatch(node, section, keys, allow_missing)
        if mismatch is None:
            return section
        mismatches.append(mismatch)
    if has_dict:
        return None
    names = ", ".join(f"`{section.__qualname__}`" for section in sections)
    raise ConfigSchemaError(
        f"The mapping fits none of {names}: {'; '.join(mismatches)}."
    )


def _find_mismatch(
    node: DictConfig, section: type, keys: list[Any], allow_missing: bool
) -> str | None:
    # Only the keys and the `Literal` values of the mapping itself are compared, so
    # that a mapping is read once however deep the unions are nested
    fields = read_fields(section)
    name = section.__qualname__
    for key in keys:
        annotation = fields[key].annotation if key in fields else None
        if get_origin(annotation) is not Literal:
            continue
        value = read_value(node, key, allow_missing)
        literal_values = get_args(annotation)
        if value is not MISSING_VALUE and value not in literal_values:
            described_values = ", ".join(f"`{item!r}`" for item in literal_values)
            return f"`{name}.{key}` takes {described_values}"
    unknown_keys = [key for key in keys if key not in fields]
    if unknown_keys:
        return (
            f"{', '.join(f'`{key}`' for key in unknown_keys)} is not a field of "
            f"`{name}`"
        )
    missing_keys = [
        key for key, field in fields.items() if field.is_required and key not in keys
    ]
    if missing_keys and not allow_missing:
        return f"`{name}` requires {', '.join(f'`{key}`' for key in missing_keys)}"
    return None


def _check_schema(
    node: DictConfig,
    schema: type,
    keys: list[Any],
    active_nodes: list[Config],
    allow_missing: bool,
    is_open: bool,
    positional_keys: list[str] | tuple[str, ...] = (),
) -> dict[Any, Any]:
    try:
        fields = read_fields(schema)
        unknown_keys = [key for key in keys if key not in fields]
        if unknown_keys:
            raise ConfigSchemaError(
                f"{', '.join(f'`{key}`' for key in unknown_keys)} is not a field of "
                f"`{schema.__qualname__}`. Its fields are "
                f"{', '.join(f'`{key}`' for key in fields)}."
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
        if missing_keys and not (is_open or allow_missing):
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
        annotation = Any if fields[key].is_plain_value else fields[key].annotation
        arguments[key] = _check_value(
            node, key, active_nodes, allow_missing, annotation
        )
    try:
        plain_values = {
            key: _unwrap_plain_value(value)
            for key, value in arguments.items()
            if fields[key].is_plain_value
        }
        if allow_missing:
            # As in a tuple, a value that is or holds a missing value is not converted
            plain_values = {
                key: value
                for key, value in plain_values.items()
                if not _holds_missing_value(value)
            }
        converted_values = convert_plain_values(
            schema, plain_values, get_full_key(node)
        )
    except OmegaKitBaseException as error:
        if error.full_key is None:
            error.full_key = get_full_key(node)
        raise
    return arguments | converted_values


def _check_value(
    parent: Config,
    key: Any,
    active_nodes: list[Config],
    allow_missing: bool,
    annotation: Any,
) -> Any:
    value = read_value(parent, key, allow_missing)
    if isinstance(value, (DictConfig, ListConfig, TupleConfig)):
        value = _check_node(value, active_nodes, allow_missing, annotation)
    try:
        typed_value = _check_type(value, annotation)
    except ConfigSchemaError as error:
        if error.full_key is None:
            error.full_key = parent._get_full_key(key)
        raise
    return typed_value


def _unwrap_plain_value(value: Any) -> Any:
    if isinstance(value, Call):
        raise ConfigSchemaError(
            f"`{TARGET_KEY}: {value.name}` cannot stand in a field that holds plain "
            "values."
        )
    if not isinstance(value, Container):
        return value
    if isinstance(value.items, dict):
        return {key: _unwrap_plain_value(item) for key, item in value.items.items()}
    return type(value.items)(_unwrap_plain_value(item) for item in value.items)


def _holds_missing_value(value: Any) -> bool:
    if isinstance(value, dict):
        return any(_holds_missing_value(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_holds_missing_value(item) for item in value)
    return value is MISSING_VALUE


def _check_type(value: Any, annotation: Any) -> Any:
    # A missing value that is allowed fits every annotation
    if annotation is Any or value is MISSING_VALUE:
        return value
    members = union_members(annotation)
    # A field that is annotated with a schema takes a mapping of the config
    if any(is_typeddict(member) for member in members):
        if isinstance(value, Container) and isinstance(value.items, dict):
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
            given_value = value.items if isinstance(value, Container) else value
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
    elif isinstance(value, Container) and isinstance(value.items, dict):
        given = "a mapping"
    elif isinstance(value, Container):
        given = f"a {type(value.items).__name__}"
    else:
        given = f"`{value!r}`"
    expected = annotation.__qualname__ if isinstance(annotation, type) else annotation
    raise ConfigSchemaError(f"Expected `{expected}`, but the config gives {given}.")
