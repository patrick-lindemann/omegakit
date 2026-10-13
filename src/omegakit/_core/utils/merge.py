from collections.abc import Iterator
from typing import Any, cast

from omegaconf import MISSING, DictConfig, ListConfig, OmegaConf, TupleConfig
from omegaconf.errors import InterpolationResolutionError, MissingMandatoryValue

from omegakit._core.errors import (
    MergeCycleError,
    MergeReferenceError,
)

from .describe import describe_error, describe_node
from .walk import walk


def walk_mergeable(
    config: DictConfig | ListConfig | TupleConfig, key: str
) -> Iterator[tuple[DictConfig, Any]]:
    while True:
        holders = [
            node
            for node in walk(config, "post-order")
            if isinstance(node, DictConfig) and key in node.keys()  # noqa: SIM118
        ]
        if not holders:
            return
        holder_ids = {id(holder) for holder in holders}
        blockers: dict[int, DictConfig] = {}
        unresolved: tuple[DictConfig, InterpolationResolutionError] | None = None
        has_progressed = False
        for node in holders:
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
            parent = node._get_parent()
            while parent is not None:
                enclosing_ids.add(id(parent))
                parent = parent._get_parent()
            # What the merge reads: the node, each mapping of the value, and what
            # encloses such a mapping without enclosing the node
            read_nodes = list(walk(node))
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
            yield node, value
            has_progressed = True
        if has_progressed:
            continue
        if unresolved is not None:
            node, cause = unresolved
            error = MergeReferenceError(
                f"Cannot resolve `{key}`: {describe_error(cause)}"
            )
            error.add_note(f"  at {describe_node(node)}")
            raise error from cause
        # Every holder is blocked, so following the blockers ends in a cycle
        chain = [holders[0]]
        while sum(node is chain[-1] for node in chain) == 1:
            chain.append(blockers[id(chain[-1])])
        start = [node is chain[-1] for node in chain].index(True)
        cycle = " -> ".join(describe_node(node) for node in chain[start:])
        raise MergeCycleError(
            f"The `{key}` of these nodes wait for each other: {cycle}."
        )


def merge_under(node: DictConfig, *others: DictConfig) -> None:
    merged_config = cast(DictConfig, OmegaConf.merge(*others, node))
    # Written back key by key, so that `node` itself stays in its place
    for key in list(node.keys()):
        del node[key]
    for key in merged_config.keys():  # noqa: SIM118
        node[key] = merged_config._get_node(key)
