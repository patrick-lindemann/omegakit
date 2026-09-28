from collections.abc import Callable
from typing import Any, cast

from omegaconf import DictConfig, ListConfig, OmegaConf
from omegaconf.errors import InterpolationKeyError, OmegaConfBaseException

from .errors import (
    ConfigLoadError,
    describe_error,
    format_full_key,
    format_node_path,
)
from .keys import BASE_KEY, DEFAULTS_KEY, RESERVED_PREFIX
from .walk import walk, walk_post_order


def merge_bases(config: DictConfig | ListConfig) -> None:
    """Merge every `$base` underneath its node in place, in dependency order.

    Args:
        config: The config to process.

    Raises:
        ConfigLoadError: If a `$base` is not a mapping or a list of mappings,
            cannot be resolved, or if `$base` references form a cycle.
    """  # noqa: DOC502
    _merge_in_dependency_order(config, BASE_KEY, _merge_base)


def apply_defaults(config: DictConfig | ListConfig) -> None:
    """Merge every `$defaults` under its dict-valued siblings in place.

    Args:
        config: The config to process.

    Raises:
        ConfigLoadError: If a `$defaults` is not a mapping, cannot be resolved,
            or if `$defaults` references form a cycle.
    """  # noqa: DOC502
    _merge_in_dependency_order(config, DEFAULTS_KEY, _merge_defaults)


def _merge_in_dependency_order(
    config: DictConfig | ListConfig,
    key: str,
    merge: Callable[[DictConfig, Any], None],
) -> None:
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


def _merge_base(node: DictConfig, base: Any) -> None:
    if isinstance(base, ListConfig):
        bases = [base[index] for index in range(len(base))]
        if not all(isinstance(item, DictConfig) for item in bases):
            raise ConfigLoadError(
                f"List-valued `{BASE_KEY}` in `{format_node_path(node)}` must contain "
                "only mappings."
            )
    elif isinstance(base, DictConfig):
        bases = [base]
    else:
        raise ConfigLoadError(
            f"`{BASE_KEY}` in `{format_node_path(node)}` is not a mapping or a list of "
            "mappings."
        )
    node.pop(BASE_KEY)
    merged_config = cast(DictConfig, OmegaConf.merge(*bases, node))
    for key in list(merged_config.keys()):
        node[key] = merged_config._get_node(key)


def _merge_defaults(node: DictConfig, defaults: Any) -> None:
    if not isinstance(defaults, DictConfig):
        raise ConfigLoadError(
            f"`{DEFAULTS_KEY}` in `{format_node_path(node)}` is not a mapping."
        )
    node.pop(DEFAULTS_KEY)
    for key, item in list(node.items_ex(resolve=False)):
        if not str(key).startswith(RESERVED_PREFIX) and isinstance(item, DictConfig):
            node[key] = OmegaConf.merge(defaults, item)


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
