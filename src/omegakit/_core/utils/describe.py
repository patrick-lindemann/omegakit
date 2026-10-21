from omegaconf import Node
from yaml import MarkedYAMLError


def get_full_key(node: Node) -> str:
    """Find the full key of a node.

    Args:
        node: The node.

    Returns:
        The full key, such as `model.layers[0]`, or `""` for the root.
    """
    parent = node._get_parent()
    if parent is None:
        return ""
    # The node's own `_get_full_key` drops the brackets of a list index
    return parent._get_full_key(node._key())


def describe_node(node: Node) -> str:
    """Describe a node for a message.

    Args:
        node: The node.

    Returns:
        The full key in backticks, or "the root".
    """
    full_key = get_full_key(node)
    return f"`{full_key}`" if full_key else "the root"


def describe_error(error: Exception) -> str:
    """Describe an error in one line.

    Args:
        error: The error.

    Returns:
        The first line of the message, with the position of a YAML error, or the
        class name for an empty message.
    """
    if isinstance(error, MarkedYAMLError):
        context = f"{error.context}: " if error.context else ""
        mark = error.problem_mark
        position = f" (line {mark.line + 1}, column {mark.column + 1})" if mark else ""
        return f"{context}{error.problem}{position}"
    lines = str(error).splitlines()
    return lines[0] if lines else type(error).__name__
