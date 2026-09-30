from typing import Any, cast

from omegaconf import DictConfig, ListConfig, Node

from omegakit.core.errors import ConfigLoadError


def select_node(
    config: DictConfig | ListConfig, node_path: str, resolve: bool = False
) -> Node | None:
    """Select a node by a dotted path, such as `items.0.name`, without resolving it.

    Args:
        config: The config to select from.
        node_path: The dotted path from `config`.
        resolve: Follow an interpolation on the way, such as `a` in `a.b` for
            `a: ${other}`. Defaults to `False`.

    Returns:
        The selected node, unresolved, or `None` if there is none at `node_path`.

    Raises:
        ConfigLoadError: If the path goes through an interpolation and `resolve`
            is `False`.
    """
    node: Any = config
    walked: list[str] = []
    for part in filter(None, node_path.split(".")):
        if isinstance(node, Node) and node._is_interpolation():
            if not resolve:
                raise ConfigLoadError(
                    f"Node path `{node_path}` goes through `{'.'.join(walked)}`, "
                    "which is an interpolation."
                )
            node = cast(Any, node._get_parent_container())[node._key()]
        if isinstance(node, DictConfig):
            node = node._get_node(part)
        elif (
            isinstance(node, ListConfig)
            and part.lstrip("-").isdigit()
            and -len(node) <= int(part) < len(node)
        ):
            node = node._get_node(int(part))
        else:
            return None
        if node is None:
            return None
        walked.append(part)
    return node
