from typing import Any

from yaml import MarkedYAMLError


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
