import importlib
from collections.abc import Callable, Iterator
from typing import Any

from omegaconf import DictConfig, ListConfig

from .keys import CLASS_KEY


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


def node(target: Callable[..., Any], /, **kwargs: Any) -> dict[str, Any]:
    """Create an instantiable config node for a class or function.

    Use it inside `from_config` for children that code chooses, such as
    `instantiate(node(Encoder, width=8), Encoder)`.

    Args:
        target: The class or function to build. It must be defined at module level.
        **kwargs: The node's arguments.

    Returns:
        The node: `kwargs` plus `$class` set to the import path of `target`.

    Raises:
        ValueError: If `target` is defined inside a function or a class, where it
            cannot be imported by its path.
    """
    qualname = target.__qualname__
    if "." in qualname:
        raise ValueError(
            f"Cannot create a node for `{qualname}`: only objects defined at module "
            "level can be imported by their path."
        )
    return {CLASS_KEY: f"{target.__module__}.{qualname}", **kwargs}


def format_path(path: tuple[str | int, ...]) -> str:
    """Format a node path from the config root, such as `items.0.model`.

    Args:
        path: The keys and list indices from the root.

    Returns:
        The dotted path, or `<root>` for the root itself.
    """
    return ".".join(map(str, path)) or "<root>"


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
