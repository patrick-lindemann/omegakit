import re

from omegaconf import Node


def format_path(path: tuple[str | int, ...]) -> str:
    """Format a node path from the config root.

    Args:
        path: The keys and list indices from the root.

    Returns:
        The dotted path, or `<root>` for the root itself.
    """
    return ".".join(map(str, path)) or "<root>"


def format_node_path(node: Node) -> str:
    """Format the path of a config node from its root.

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
    """Format the `full_key` of an OmegaConf error.

    Args:
        full_key: The key path, with list indices in brackets.

    Returns:
        The dotted path, or `<root>` for an empty one.
    """
    return re.sub(r"\[(-?\d+)\]", r".\1", full_key).lstrip(".") or "<root>"
