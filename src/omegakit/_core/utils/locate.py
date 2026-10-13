import importlib
from typing import Any

from omegakit._core.errors import (
    QualifiedNameNotFoundError,
    QualifiedNameSyntaxError,
)

_NOT_FOUND = object()


def locate(qualified_name: str) -> Any:
    module_path, _, attr_name = qualified_name.rpartition(".")
    if not all(qualified_name.split(".")) or not module_path:
        raise QualifiedNameSyntaxError(
            f"`{qualified_name}` is not an import path of the form "
            "`package.module.Name`."
        )
    try:
        module = importlib.import_module(module_path)
    except ModuleNotFoundError as error:
        # A module that the target's own module fails to import is a missing
        # dependency, not a mistake in the config
        if error.name is None or not f"{module_path}.".startswith(f"{error.name}."):
            raise
        raise QualifiedNameNotFoundError(
            f"There is no module `{error.name}`."
        ) from error
    target = getattr(module, attr_name, _NOT_FOUND)
    if target is not _NOT_FOUND:
        return target
    try:
        # A submodule is no attribute of its package before it is imported
        return importlib.import_module(qualified_name)
    except ModuleNotFoundError as error:
        if error.name != qualified_name:
            raise
        raise QualifiedNameNotFoundError(
            f"Module `{module_path}` has no attribute `{attr_name}`."
        ) from error
