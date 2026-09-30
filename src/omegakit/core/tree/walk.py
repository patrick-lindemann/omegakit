from collections.abc import Iterator

from omegaconf import DictConfig, ListConfig


def walk(config: DictConfig | ListConfig) -> Iterator[DictConfig]:
    """Walk along every mapping node in `config` depth-first.

    Args:
        config: The config to traverse.

    Yields:
        Each mapping node, parents before children.
    """
    if isinstance(config, DictConfig):
        yield config
        children = [node for _, node in config.items_ex(resolve=False)]
    else:
        children = [config._get_node(index) for index in range(len(config))]
    for node in children:
        if isinstance(node, (DictConfig, ListConfig)):
            yield from walk(node)


def walk_post_order(config: DictConfig | ListConfig) -> Iterator[DictConfig]:
    """Walk along every mapping node in `config` depth-first, children first.

    Args:
        config: The config to traverse.

    Yields:
        Each mapping node, children before parents.
    """
    if isinstance(config, DictConfig):
        children = [node for _, node in config.items_ex(resolve=False)]
    else:
        children = [config._get_node(index) for index in range(len(config))]
    for node in children:
        if isinstance(node, (DictConfig, ListConfig)):
            yield from walk_post_order(node)
    if isinstance(config, DictConfig):
        yield config


def strip_keys(config: DictConfig | ListConfig, exclude: set[str]) -> None:
    """Remove the keys in `exclude` from every mapping node of `config` in place.

    Args:
        config: The config to process.
        exclude: The keys to remove.
    """
    for node in walk(config):
        for key in list(node.keys()):
            if key in exclude:
                node.pop(key)
