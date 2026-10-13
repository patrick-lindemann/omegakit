import importlib
from typing import Any

from .error import OmegaKitBaseException

_NOT_FOUND = object()


class PathSyntaxError(OmegaKitBaseException, ValueError):
    pass


class PathNotFoundError(OmegaKitBaseException, ImportError):
    pass


def import_path(path: str) -> Any:
    module_path, _, attr_name = path.rpartition(".")
    if not all(path.split(".")) or not module_path:
        raise PathSyntaxError(
            f"`{path}` is not an import path of the form `package.module.Name`."
        )
    try:
        module = importlib.import_module(module_path)
    except ModuleNotFoundError as error:
        # A module that the target's own module fails to import is a missing
        # dependency, not a mistake in the config
        if error.name is None or not f"{module_path}.".startswith(f"{error.name}."):
            raise
        raise PathNotFoundError(f"There is no module `{error.name}`.") from error
    target = getattr(module, attr_name, _NOT_FOUND)
    if target is _NOT_FOUND:
        raise PathNotFoundError(
            f"Module `{module_path}` has no attribute `{attr_name}`."
        )
    return target
