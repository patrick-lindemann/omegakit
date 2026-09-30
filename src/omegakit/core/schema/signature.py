import functools
import inspect
import sys
import types
from typing import Any, TypeAliasType, Union, get_args, get_origin, get_type_hints

from omegakit.core.errors import SchemaDefinitionError

from .configurable import Configurable
from .field import classify_fields
from .lookup import find_schema


@functools.cache
def check_schema(cls: type) -> None:
    """Check that the schema of `cls` matches its `__init__`.

    Args:
        cls: The class to check.

    Raises:
        SchemaDefinitionError: If the schema is not supported, a required parameter
            has no field, a field has no parameter and `__init__` takes no
            `**kwargs`, or a field's annotation is not assignable to its
            parameter's annotation.
        TypeError: If `cls` is not a class.
    """  # noqa: DOC503
    schema = find_schema(cls)
    if (
        schema is None
        or schema is cls
        or any(
            "from_config" in vars(base)
            for base in cls.__mro__
            if base is not Configurable
        )
    ):
        return
    fields = classify_fields(schema)
    parameters = inspect.signature(cls).parameters
    hints = _init_hints(cls)
    keyword_names = {
        name
        for name, parameter in parameters.items()
        if parameter.kind
        in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
    }
    takes_kwargs = any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD
        for parameter in parameters.values()
    )
    for name, parameter in parameters.items():
        if (
            parameter.default is inspect.Parameter.empty
            and parameter.kind
            not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
            and name not in fields
        ):
            raise SchemaDefinitionError(
                f"Schema `{schema.__qualname__}` of `{cls.__qualname__}` has no field "
                f"for the required parameter `{name}`."
            )
    for name, (_, annotation) in fields.items():
        if name not in keyword_names:
            positional = name in parameters and (
                parameters[name].kind is inspect.Parameter.POSITIONAL_ONLY
            )
            if takes_kwargs and not positional:
                continue
            reason = (
                "takes it only positionally" if positional else "takes no `**kwargs`"
            )
            raise SchemaDefinitionError(
                f"Field `{name}` of schema `{schema.__qualname__}` is not a keyword "
                f"parameter of `{cls.__qualname__}`, and `__init__` {reason}."
            )
        if name in hints and not _is_assignable(annotation, hints[name]):
            raise SchemaDefinitionError(
                f"Field `{name}` of schema `{schema.__qualname__}` has `{annotation}`, "
                f"which is not assignable to `{hints[name]}` in "
                f"`{cls.__qualname__}.__init__`."
            )


def _init_hints(cls: type) -> dict[str, Any]:
    try:
        return get_type_hints(cls.__init__)
    except Exception:
        # Annotations imported under `TYPE_CHECKING` do not resolve; check the rest.
        hints = {}
        for name, annotation in getattr(cls.__init__, "__annotations__", {}).items():
            try:
                hints[name] = (
                    eval(annotation, vars(sys.modules[cls.__init__.__module__]))
                    if isinstance(annotation, str)
                    else annotation
                )
            except Exception:
                continue
        return hints


def _is_assignable(source: Any, target: Any) -> bool:
    while isinstance(source, TypeAliasType):
        source = source.__value__
    while isinstance(target, TypeAliasType):
        target = target.__value__
    if source is Any or target is Any:
        return True
    if get_origin(source) in (Union, types.UnionType):
        return all(_is_assignable(member, target) for member in get_args(source))
    if get_origin(target) in (Union, types.UnionType):
        return any(_is_assignable(source, member) for member in get_args(target))
    if get_origin(source) is not None or get_origin(target) is not None:
        return True
    if not (isinstance(source, type) and isinstance(target, type)):
        return True
    if target is float and source is int:
        return True
    if target is complex and source in (int, float):
        return True
    return issubclass(source, target)
