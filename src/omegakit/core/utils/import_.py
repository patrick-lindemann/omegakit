import importlib
from typing import Any


def import_object(import_path: str) -> Any:
    """Import an object by its dotted path.

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
