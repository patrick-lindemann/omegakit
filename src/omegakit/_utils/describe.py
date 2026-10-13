from omegaconf import Node
from yaml import MarkedYAMLError


def describe_node(node: Node) -> str:
    parent = node._get_parent()
    if parent is None:
        return "the root"
    # The node's own `_get_full_key` drops the brackets of a list index
    return f"`{parent._get_full_key(node._key())}`"


def describe_error(error: Exception) -> str:
    if isinstance(error, MarkedYAMLError):
        context = f"{error.context}: " if error.context else ""
        mark = error.problem_mark
        position = f" (line {mark.line + 1}, column {mark.column + 1})" if mark else ""
        return f"{context}{error.problem}{position}"
    lines = str(error).splitlines()
    return lines[0] if lines else type(error).__name__
