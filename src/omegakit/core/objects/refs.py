from typing import Any

from omegakit.core.errors import ConfigValidationError
from omegakit.core.utils import format_path

from .targets import import_target

REF_KEY = "$ref"
"""Import path of an object that replaces the node without being called."""


def import_ref(
    node: dict[str, Any],
    path: tuple[str | int, ...],
    allowed_modules: tuple[str, ...] | None,
) -> Any:
    """Import the object that a `$ref` node names.

    Args:
        node: The resolved node.
        path: The node's path from the config root.
        allowed_modules: The modules that `$ref` may name, as in `import_target`.

    Returns:
        The imported object.

    Raises:
        ConfigValidationError: If the node has other keys, or the object cannot be
            imported as `import_target` says.
        ImportError: If the named module fails to import a module of its own.
    """  # noqa: DOC503
    if len(node) > 1:
        raise ConfigValidationError(
            f"A node using `{REF_KEY}` cannot contain any other keys, but "
            f"`{format_path(path)}` has {', '.join(f'`{key}`' for key in node)}."
        )
    return import_target(node, REF_KEY, path, allowed_modules)
