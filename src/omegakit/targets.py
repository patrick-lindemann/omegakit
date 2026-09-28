import importlib
from collections.abc import Callable
from typing import Any

from .keys import CLASS_KEY


def import_object(import_path: str) -> Any:
    """Import an object by its dotted path, such as `package.module.Name`.

    Args:
        import_path: The module path and attribute name, separated by a dot.

    Returns:
        The imported object.

    Raises:
        ImportError: If `import_path` is not a dotted path of at least two names, if
            the module cannot be imported, or if it has no attribute of that name.
            The first and the last carry `import_path` as their `name`.
    """
    if not all(import_path.split(".")) or "." not in import_path:
        raise ImportError(
            f"`{import_path}` is not an import path of the form `package.module.Name`.",
            name=import_path,
        )
    module_path, _, attr_name = import_path.rpartition(".")
    module = importlib.import_module(module_path)
    try:
        return getattr(module, attr_name)
    except AttributeError as error:
        raise ImportError(
            f"Module `{module_path}` has no attribute `{attr_name}`.",
            name=import_path,
        ) from error


def make_node(target: Callable[..., Any], /, **kwargs: Any) -> dict[str, Any]:
    """Create an instantiable config node for a class or function.

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
