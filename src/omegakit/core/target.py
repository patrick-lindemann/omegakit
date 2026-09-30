from typing import Any

from .errors import ConfigValidationError
from .utils import describe_value, format_path, import_object


def import_target(
    node: dict[str, Any],
    key: str,
    path: tuple[str | int, ...],
    allowed_modules: tuple[str, ...] | None,
) -> Any:
    """Import the object that the `$class` or `$ref` of a node names.

    Args:
        node: The resolved node.
        key: `$class` or `$ref`.
        path: The node's path from the config root.
        allowed_modules: The modules, with their submodules, that `key` may name,
            or `None` for every module.

    Returns:
        The imported object.

    Raises:
        ConfigValidationError: If the import path is not a string, names a module
            that is not allowed, or cannot be imported.
        ImportError: If the named module fails to import a module of its own, such
            as a missing dependency.
    """  # noqa: DOC503
    import_path = node[key]
    if not isinstance(import_path, str):
        raise ConfigValidationError(
            f"`{key}` in `{format_path(path)}` must be an import path, such as "
            "`package.module.Name`, but the config gives "
            f"{describe_value(import_path)}."
        )
    # Checked before the import, so that a module that is not allowed never runs.
    if not _is_allowed(import_path.rpartition(".")[0], allowed_modules):
        raise ConfigValidationError(
            f"`{key}: {import_path}` in `{format_path(path)}` names a module that "
            "is not in `allowed_modules`."
        )
    try:
        target = import_object(import_path)
    except ImportError as error:
        # A module that the target's own module fails to import is a missing
        # dependency, not a mistake in the config.
        parts = import_path.split(".")
        targets = {".".join(parts[:end]) for end in range(1, len(parts))}
        if error.name != import_path and not (
            isinstance(error, ModuleNotFoundError) and error.name in targets
        ):
            raise
        raise ConfigValidationError(
            f"Cannot import `{import_path}` in `{format_path(path)}`: {error}"
        ) from error
    # An allowed module can import a name from a module that is not allowed.
    module = getattr(target, "__module__", None)
    if isinstance(module, str) and not _is_allowed(module, allowed_modules):
        raise ConfigValidationError(
            f"`{key}: {import_path}` in `{format_path(path)}` is defined in "
            f"`{module}`, which is not in `allowed_modules`."
        )
    return target


def _is_allowed(module: str, allowed_modules: tuple[str, ...] | None) -> bool:
    return allowed_modules is None or any(
        module == allowed or module.startswith(f"{allowed}.")
        for allowed in allowed_modules
    )
