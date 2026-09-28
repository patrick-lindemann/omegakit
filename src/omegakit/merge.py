from collections.abc import Callable
from typing import Any, cast

from omegaconf import DictConfig, ListConfig, OmegaConf
from omegaconf.errors import InterpolationKeyError, OmegaConfBaseException

from .errors import ConfigLoadError, format_node_path
from .keys import BASE_KEY, DEFAULTS_KEY
from .walk import walk, walk_post_order


def merge_bases(config: DictConfig | ListConfig) -> None:
    """Merge every `$base` underneath its node in place, in dependency order.

    Args:
        config: The config to process.

    Raises:
        ConfigLoadError: If a `$base` is not a mapping or a list of mappings,
            cannot be resolved, or if `$base` references form a cycle.
    """
    cycle = _merge_in_dependency_order(config, BASE_KEY, _merge_base)
    if cycle:
        nodes = ", ".join(f"`{format_node_path(node)}`" for node in cycle)
        raise ConfigLoadError(f"`{BASE_KEY}` references form a cycle between {nodes}.")


def apply_defaults(config: DictConfig | ListConfig) -> None:
    """Merge every `$defaults` under its dict-valued siblings in place.

    Args:
        config: The config to process.

    Raises:
        ConfigLoadError: If a `$defaults` is not a mapping, cannot be resolved,
            or if `$defaults` references form a cycle.
    """
    cycle = _merge_in_dependency_order(config, DEFAULTS_KEY, _merge_defaults)
    if cycle:
        nodes = ", ".join(f"`{format_node_path(node)}`" for node in cycle)
        raise ConfigLoadError(
            f"`{DEFAULTS_KEY}` references form a cycle between {nodes}."
        )


def _merge_in_dependency_order(
    config: DictConfig | ListConfig,
    key: str,
    merge: Callable[[DictConfig, Any], None],
) -> list[DictConfig]:
    while True:
        waiting: list[DictConfig] = []
        blocked: set[int] = set()
        first_error: OmegaConfBaseException | None = None
        merged = False
        for node in list(walk_post_order(config)):
            if node._get_node(key) is None:
                continue
            if id(node) not in blocked:
                try:
                    value = node[key]
                except InterpolationKeyError as error:
                    if first_error is None:
                        first_error = error
                else:
                    referenced = value if isinstance(value, ListConfig) else [value]
                    if not any(
                        isinstance(item, DictConfig)
                        and any(
                            inner._get_node(key) is not None for inner in walk(item)
                        )
                        for item in referenced
                    ):
                        merge(node, value)
                        merged = True
                        continue
            waiting.append(node)
            # Merging an ancestor replaces its children, so ancestors wait too.
            parent = node._get_parent()
            while parent is not None and id(parent) not in blocked:
                blocked.add(id(parent))
                parent = parent._get_parent()
        if not waiting:
            return []
        if not merged:
            if first_error is not None:
                raise ConfigLoadError(
                    f"Cannot resolve `{first_error.full_key or key}`: "
                    f"{str(first_error).splitlines()[0]}"
                ) from first_error
            return waiting


def _merge_base(node: DictConfig, base: Any) -> None:
    # A base may be a single mapping or a list of mappings. Later list elements take
    # precedence over earlier ones, and the node's own keys over all.
    if isinstance(base, ListConfig):
        bases = [base[index] for index in range(len(base))]
        if not all(isinstance(item, DictConfig) for item in bases):
            raise ConfigLoadError(
                f"List-valued `{BASE_KEY}` in `{format_node_path(node)}` must contain "
                "only dictionaries."
            )
    elif isinstance(base, DictConfig):
        bases = [base]
    else:
        raise ConfigLoadError(
            f"`{BASE_KEY}` in `{format_node_path(node)}` is not a dictionary or a list "
            "of dictionaries."
        )
    node.pop(BASE_KEY)
    merged_config = cast(DictConfig, OmegaConf.merge(*bases, node))
    for key in list(merged_config.keys()):
        node[key] = merged_config._get_node(key)


def _merge_defaults(node: DictConfig, defaults: Any) -> None:
    if not isinstance(defaults, DictConfig):
        raise ConfigLoadError(
            f"`{DEFAULTS_KEY}` in `{format_node_path(node)}` is not a dictionary."
        )
    node.pop(DEFAULTS_KEY)
    for key in list(node.keys()):
        if str(key).startswith("$"):
            continue
        item = node._get_node(key)
        if isinstance(item, DictConfig):
            node[key] = OmegaConf.merge(defaults, item)
