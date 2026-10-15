from collections.abc import Iterator
from typing import Any, cast

from omegaconf import MISSING, DictConfig, ListConfig, Node, OmegaConf, TupleConfig
from omegaconf.errors import InterpolationResolutionError, MissingMandatoryValue

from omegakit._core.errors import (
    ConfigMergeError,
)

from .describe import describe_error, describe_node, get_full_key
from .walk import WalkOrder, walk


def walk_mergeable(
    config: DictConfig | ListConfig | TupleConfig,
    key: str,
    is_outer_first: bool = False,
) -> Iterator[tuple[DictConfig, Any]]:
    # In this order a holder comes after every holder it usually waits for
    order: WalkOrder = "pre-order" if is_outer_first else "post-order"
    while True:
        holders = [
            node
            for node in walk(config, order)
            if isinstance(node, DictConfig) and key in node.keys()  # noqa: SIM118
        ]
        # The consumer deletes `key` from every node it is given, or this never ends
        if not holders:
            return
        holder_ids = {id(holder) for holder in holders}
        # The holders below a merged node, which the merge replaced by copies
        replaced_ids: set[int] = set()
        blockers: dict[int, DictConfig] = {}
        unresolved: tuple[DictConfig, InterpolationResolutionError] | None = None
        has_progressed = False
        for node in holders:
            if id(node) in replaced_ids:
                continue
            try:
                value = node[key]
                items = list(value) if isinstance(value, ListConfig) else [value]
            except MissingMandatoryValue:
                value = MISSING
                items = []
            except InterpolationResolutionError as error:
                if unresolved is None:
                    unresolved = (node, error)
                continue
            enclosing_ids: set[int] = set()
            enclosing_nodes: list[Node] = []
            child: Node = node
            parent = node._get_parent()
            while parent is not None:
                enclosing_ids.add(id(parent))
                # A node inside the value of `key` is read by that merge, not
                # changed by it
                if not (
                    isinstance(parent, DictConfig)
                    and key in parent.keys()  # noqa: SIM118
                    and parent._get_node(key) is child
                ):
                    enclosing_nodes.append(parent)
                child = parent
                parent = parent._get_parent()
            # What the merge reads: the node, each mapping of the value, and what
            # encloses such a mapping without enclosing the node. Outer first, the
            # node waits for what encloses it instead of what it encloses.
            read_nodes = enclosing_nodes if is_outer_first else list(walk(node))
            for item in items:
                if not isinstance(item, DictConfig):
                    continue
                read_nodes.extend(walk(item))
                parent = item._get_parent()
                while parent is not None and id(parent) not in enclosing_ids:
                    read_nodes.append(parent)
                    parent = parent._get_parent()
            pending_nodes = [
                read_node
                for read_node in read_nodes
                if read_node is not node
                and id(read_node) in holder_ids
                and isinstance(read_node, DictConfig)
                and key in read_node.keys()  # noqa: SIM118
            ]
            if pending_nodes:
                blockers[id(node)] = pending_nodes[0]
                continue
            if is_outer_first:
                replaced_ids.update(
                    id(inner_node)
                    for inner_node in walk(node)
                    if inner_node is not node and id(inner_node) in holder_ids
                )
            yield node, value
            has_progressed = True
        if has_progressed:
            continue
        if unresolved is not None:
            node, cause = unresolved
            raise ConfigMergeError(
                f"Cannot resolve `{key}`: {describe_error(cause)}", get_full_key(node)
            ) from cause
        # Every holder is blocked, so following the blockers ends in a cycle
        chain = [holders[0]]
        while sum(node is chain[-1] for node in chain) == 1:
            chain.append(blockers[id(chain[-1])])
        start = [node is chain[-1] for node in chain].index(True)
        cycle = " -> ".join(describe_node(node) for node in chain[start:])
        raise ConfigMergeError(
            f"The `{key}` of these nodes wait for each other: {cycle}."
        )


def merge_under(node: DictConfig, *others: DictConfig) -> None:
    merged_config = cast(DictConfig, OmegaConf.merge(*others, node))
    _write_back(node, merged_config)


def merge_over(node: DictConfig, *others: DictConfig) -> None:
    merged_config = cast(DictConfig, OmegaConf.merge(node, *others))
    _write_back(node, merged_config)


def _write_back(node: DictConfig, merged_config: DictConfig) -> None:
    # Written back key by key, so that `node` itself stays in its place
    for key in list(node.keys()):
        del node[key]
    for key in merged_config.keys():  # noqa: SIM118
        node[key] = merged_config._get_node(key)
