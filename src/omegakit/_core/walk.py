from collections.abc import Iterator
from typing import Literal, cast

from omegaconf import DictConfig, ListConfig, Node, TupleConfig

type WalkOrder = Literal["pre-order", "post-order"]


def walk(node: Node, order: WalkOrder = "pre-order") -> Iterator[Node]:
    match order:
        case "pre-order":
            yield from walk_pre_order(node)
        case "post-order":
            yield from walk_post_order(node)
        case _:
            raise ValueError(f"Invalid walk order `{order}`.")


def walk_pre_order(node: Node) -> Iterator[Node]:
    yield node
    for child in _get_children(node):
        yield from walk_pre_order(child)


def walk_post_order(node: Node) -> Iterator[Node]:
    for child in _get_children(node):
        yield from walk_post_order(child)
    yield node


def _get_children(node: Node) -> list[Node]:
    if isinstance(node, DictConfig):
        return [cast(Node, node._get_node(key)) for key in node]
    if isinstance(node, (ListConfig, TupleConfig)):
        return [cast(Node, node._get_node(index)) for index in range(len(node))]
    return []
