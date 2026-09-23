from collections.abc import Iterator

from omegaconf import DictConfig, ListConfig, OmegaConf


def walk(config: DictConfig | ListConfig) -> Iterator[DictConfig]:
    """Walk along every mapping node in `config` depth-first.

    Args:
        config (DictConfig | ListConfig): The config to traverse.

    Yields:
        DictConfig: Each mapping node, parents before children.
    """
    if OmegaConf.is_dict(config):
        yield config
        children = [node for _, node in config.items_ex(resolve=False)]
    else:
        children = [config._get_node(index) for index in range(len(config))]
    for node in children:
        if OmegaConf.is_config(node):
            yield from walk(node)
