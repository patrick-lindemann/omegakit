import importlib
from collections.abc import Iterator
from typing import Any

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


def import_object(import_path: str) -> Any:
    """Import an object by its dotted path, such as `package.module.Name`.

    Args:
        import_path: The module path and attribute name, separated by a dot.

    Returns:
        The imported object.

    Raises:
        ImportError: If the module has no attribute of that name.
    """
    module_path, _, attr_name = import_path.rpartition(".")
    module = importlib.import_module(module_path)
    try:
        return getattr(module, attr_name)
    except AttributeError as error:
        raise ImportError(
            f"Could not import `{attr_name}` from module `{module_path}`. Make sure "
            "the import name is correct, and that dependencies are installed, if "
            "necessary."
        ) from error
