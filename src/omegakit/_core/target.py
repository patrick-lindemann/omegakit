import importlib
from typing import Any

from .error import OmegaKitBaseException

_NOT_FOUND = object()


class TargetSyntaxError(OmegaKitBaseException, ValueError):
    pass


class TargetNotFoundError(OmegaKitBaseException, ImportError):
    pass


def import_target(import_path: str) -> Any:
    module_path, _, attr_name = import_path.rpartition(".")
    if not all(import_path.split(".")) or not module_path:
        raise TargetSyntaxError(
            f"`{import_path}` is not an import path of the form `package.module.Name`."
        )
    try:
        module = importlib.import_module(module_path)
    except ModuleNotFoundError as error:
        # A module that the target's own module fails to import is a missing
        # dependency, not a mistake in the config
        if error.name is None or not f"{module_path}.".startswith(f"{error.name}."):
            raise
        raise TargetNotFoundError(f"There is no module `{error.name}`.") from error
    target = getattr(module, attr_name, _NOT_FOUND)
    if target is _NOT_FOUND:
        raise TargetNotFoundError(
            f"Module `{module_path}` has no attribute `{attr_name}`."
        )
    return target
