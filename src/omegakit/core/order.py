from collections.abc import Callable
from typing import Any

from omegaconf import DictConfig, ListConfig
from omegaconf.errors import InterpolationKeyError, OmegaConfBaseException

from .errors import ConfigLoadError
from .utils import describe_error, format_full_key, format_node_path
from .walk import walk, walk_post_order


def merge_in_dependency_order(
    config: DictConfig | ListConfig,
    key: str,
    merge: Callable[[DictConfig, Any], None],
) -> None:
    """Merge the value of `key` into every node that holds it, in dependency order.

    Args:
        config: The config to process.
        key: The special key whose value is merged.
        merge: Merges the resolved value into the node that holds `key`, and
            removes `key` from it.

    Raises:
        ConfigLoadError: If a value cannot be resolved, or if the references of the
            values form a cycle.
    """
    while True:
        waiting: list[DictConfig] = []
        # The nodes that each waiting node waits for, by `id`: the holders of `key`
        # inside its reference, and for an ancestor, the waiting nodes below it.
        waits_for: dict[int, list[DictConfig]] = {}
        first_error: OmegaConfBaseException | None = None
        merged = False
        for node in list(walk_post_order(config)):
            if node._get_node(key) is None:
                continue
            if id(node) not in waits_for:
                try:
                    value = node[key]
                except InterpolationKeyError as error:
                    if first_error is None:
                        first_error = error
                    waits_for[id(node)] = []
                else:
                    referenced = value if isinstance(value, ListConfig) else [value]
                    holders = [
                        inner
                        for item in referenced
                        if isinstance(item, DictConfig)
                        for inner in walk(item)
                        if inner._get_node(key) is not None
                    ]
                    if not holders:
                        merge(node, value)
                        merged = True
                        continue
                    waits_for[id(node)] = holders
            waiting.append(node)
            # Merging an ancestor replaces its children, so ancestors wait too.
            parent = node._get_parent()
            while parent is not None:
                waits_for.setdefault(id(parent), []).append(node)
                parent = parent._get_parent()
        if not waiting:
            return
        if not merged:
            if first_error is not None:
                raise ConfigLoadError(
                    f"Cannot resolve `{format_full_key(first_error.full_key or key)}`: "
                    f"{describe_error(first_error)}"
                ) from first_error
            nodes = ", ".join(
                f"`{format_node_path(node)}`"
                for node in waiting
                if _waits_for_itself(node, waits_for)
            )
            raise ConfigLoadError(f"`{key}` references form a cycle between {nodes}.")


def _waits_for_itself(node: DictConfig, waits_for: dict[int, list[DictConfig]]) -> bool:
    seen: set[int] = set()
    pending = list(waits_for[id(node)])
    while pending:
        other = pending.pop()
        if other is node:
            return True
        if id(other) not in seen:
            seen.add(id(other))
            pending.extend(waits_for[id(other)])
    return False
