import dataclasses
import functools
import types
from typing import Any, TypeVar, get_args, get_origin

from omegaconf import OmegaConf
from omegaconf.errors import OmegaConfBaseException
from typing_extensions import NoDefault

from omegakit.core.errors import OmegaKitBaseException, SchemaDefinitionError
from omegakit.core.utils import describe_error

from .configurable import Configurable
from .schema import Schema
from .structure import derive_structure


@functools.cache
def find_schema(cls: type) -> Schema | None:
    """Find the schema of a class. A schema is a plain dataclass.

    Args:
        cls: The class to inspect.

    Returns:
        `cls` itself if it is a dataclass, the `TConfig` of a `Configurable` if
        that is a dataclass, and otherwise `None`.

    Raises:
        SchemaDefinitionError: If the schema uses a dataclass feature outside the
            supported subset, or a type variable in the bases of `cls` cannot be
            resolved.
    """  # noqa: DOC503
    if issubclass(cls, Configurable):
        parameters = getattr(cls, "__parameters__", ())
        config_type = _find_config_type(
            cls,
            {parameter: _get_type_var_default(parameter) for parameter in parameters},
        )
    else:
        config_type = cls
    if not (isinstance(config_type, type) and dataclasses.is_dataclass(config_type)):
        return None
    try:
        OmegaConf.structured(derive_structure(config_type))
    except OmegaKitBaseException:
        raise
    except OmegaConfBaseException as error:
        owner = "" if config_type is cls else f" of `{cls.__qualname__}`"
        raise SchemaDefinitionError(
            f"Schema `{config_type.__qualname__}`{owner} cannot be validated by "
            f"OmegaConf: {describe_error(error)}"
        ) from error
    return config_type


def _get_type_var_default(parameter: Any) -> Any:
    return getattr(parameter, "__default__", NoDefault)


def _find_config_type(cls: type, substitutions: dict[Any, Any]) -> Any:
    for base in types.get_original_bases(cls):
        origin = get_origin(base) or base
        if not (isinstance(origin, type) and issubclass(origin, Configurable)):
            continue
        arguments = tuple(
            _substitute(argument, substitutions, cls) for argument in get_args(base)
        )
        parameters = getattr(origin, "__parameters__", ())
        if not arguments:
            arguments = tuple(
                _get_type_var_default(parameter) for parameter in parameters
            )
        if origin is Configurable:
            return arguments[0]
        return _find_config_type(origin, dict(zip(parameters, arguments, strict=True)))
    return NoDefault


def _substitute(argument: Any, substitutions: dict[Any, Any], cls: type) -> Any:
    if not isinstance(argument, TypeVar):
        return argument
    if argument not in substitutions:
        raise SchemaDefinitionError(
            f"Cannot resolve type variable `{argument}` in the bases of "
            f"`{cls.__qualname__}`."
        )
    return substitutions[argument]
