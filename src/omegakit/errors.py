import re
from typing import Any

from omegaconf import Node
from omegaconf.errors import OmegaConfBaseException, ValidationError
from yaml import MarkedYAMLError


class OmegaKitBaseException(OmegaConfBaseException):
    """The base of every error that omegakit raises about a config or a schema."""

    __module__ = "omegakit"


class ConfigLoadError(OmegaKitBaseException, ValueError):
    """A config file, an import, a `$base`, a `$defaults` or an override is invalid."""

    __module__ = "omegakit"


class ConfigValidationError(OmegaKitBaseException, ValidationError):
    """A config does not match the schema of the class it builds."""

    __module__ = "omegakit"


class SchemaDefinitionError(OmegaKitBaseException, ValueError):
    """A class cannot serve as a schema."""

    __module__ = "omegakit"


def format_path(path: tuple[str | int, ...]) -> str:
    """Format a node path from the config root, such as `items.0.model`.

    Args:
        path: The keys and list indices from the root.

    Returns:
        The dotted path, or `<root>` for the root itself.
    """
    return ".".join(map(str, path)) or "<root>"


def format_node_path(node: Node) -> str:
    """Format the path of a config node from its root, such as `items.0.model`.

    Args:
        node: The node.

    Returns:
        The dotted path, or `<root>` for the root itself.
    """
    keys = []
    while (parent := node._get_parent()) is not None:
        keys.append(node._key())
        node = parent
    return format_path(tuple(reversed(keys)))


def format_full_key(full_key: str) -> str:
    """Format the `full_key` of an OmegaConf error, such as `items[0].model`.

    Args:
        full_key: The key path, with list indices in brackets.

    Returns:
        The dotted path, such as `items.0.model`, or `<root>` for an empty one.
    """
    return re.sub(r"\[(-?\d+)\]", r".\1", full_key).lstrip(".") or "<root>"


def describe_value(value: Any) -> str:
    """Describe a config value for an error message, without a container's items.

    Args:
        value: The value.

    Returns:
        The `repr` of a scalar in backticks, the keys of a mapping, or the length of a
        list.
    """
    if isinstance(value, dict):
        keys = ", ".join(f"`{key}`" for key in value)
        return f"a mapping with keys {keys}" if keys else "an empty mapping"
    if isinstance(value, (list, tuple)):
        return f"a list of {len(value)} items"
    return f"`{value!r}`"


def describe_error(error: Exception) -> str:
    """Describe an error from PyYAML, OmegaConf or Python in one line.

    Args:
        error: The error.

    Returns:
        PyYAML's problem with its context and position, or the first line of the
        message of any other error.
    """
    if isinstance(error, MarkedYAMLError):
        context = f"{error.context}: " if error.context else ""
        mark = error.problem_mark
        position = f" (line {mark.line + 1}, column {mark.column + 1})" if mark else ""
        return f"{context}{error.problem}{position}"
    lines = str(error).splitlines()
    return lines[0] if lines else type(error).__name__
