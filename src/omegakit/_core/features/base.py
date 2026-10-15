import copy as copy_module

from omegaconf import DictConfig, ListConfig, TupleConfig

from omegakit._core.errors import (
    ConfigMergeError,
)
from omegakit._core.utils.copy import copy_with_root
from omegakit._core.utils.describe import get_full_key
from omegakit._core.utils.merge import merge_over, merge_under, walk_mergeable

BASE_KEY = "$base"
"""The key of a mapping, or a list of mappings, merged under its node."""


def merge_bases[TConfig: DictConfig | ListConfig | TupleConfig](
    config: TConfig, copy: bool = True
) -> TConfig:
    if copy:
        config = copy_with_root(config)
    # The nodes with a `$base` that an enclosing `$base` adds keys to, by full key,
    # as written
    own_contents: dict[str, DictConfig] = {}
    for node, base in walk_mergeable(config, BASE_KEY, is_outer_first=True):
        bases = list(base) if isinstance(base, ListConfig) else [base]
        if not all(isinstance(item, DictConfig) for item in bases):
            raise ConfigMergeError(
                f"`{BASE_KEY}` must be a mapping or a list of mappings, not "
                f"`{base!r}`.",
                get_full_key(node),
            )
        _save_reached_holders(node, bases, own_contents)
        del node[BASE_KEY]
        own_content = (
            own_contents.pop(get_full_key(node), None) if own_contents else None
        )
        if own_content is None:
            merge_under(node, *bases)
        else:
            # What enclosing bases brought in goes under the node's own bases, and
            # its own keys stay strongest
            del own_content[BASE_KEY]
            merge_over(node, *bases, own_content)
    return config


def _save_reached_holders(
    node: DictConfig, bases: list[DictConfig], own_contents: dict[str, DictConfig]
) -> None:
    for key in node.keys():  # noqa: SIM118
        child = node._get_node(key)
        if not isinstance(child, DictConfig):
            continue
        child_bases: list[DictConfig] = []
        for item in bases:
            base_child = item._get_node(key)
            # OmegaConf merges into the mapping that an interpolation gives
            if base_child is not None:
                base_child = base_child._maybe_dereference_node()
            if isinstance(base_child, DictConfig):
                child_bases.append(base_child)
        if not child_bases:
            continue
        if BASE_KEY in child.keys():  # noqa: SIM118
            full_key = get_full_key(child)
            if full_key not in own_contents:
                own_contents[full_key] = copy_module.deepcopy(child)
        _save_reached_holders(child, child_bases, own_contents)
