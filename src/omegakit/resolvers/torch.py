import importlib
from typing import Any

from omegaconf import OmegaConf

from ._register import register_resolver


def register_torch_dtype_resolver(*, replace: bool = False) -> None:
    """Register `${dtype:float32}`, which gives the Torch dtype of that name.

    Args:
        replace: Replace a resolver named `dtype`. Defaults to `False`.

    Raises:
        ImportError: If Torch is not installed.
        ValueError: If a resolver named `dtype` exists and `replace` is `False`.
    """  # noqa: DOC502
    _import_torch()
    register_resolver("dtype", _resolve_dtype, replace=replace)


def register_cuda_available_resolver(*, replace: bool = False) -> None:
    """Register `${cuda_available:}`, which gives whether Torch can use CUDA.

    Args:
        replace: Replace a resolver named `cuda_available`. Defaults to `False`.

    Raises:
        ImportError: If Torch is not installed.
        ValueError: If a resolver named `cuda_available` exists and `replace` is
            `False`.
    """  # noqa: DOC502
    _import_torch()
    register_resolver("cuda_available", _cuda_available, replace=replace)


def register_torch_resolvers(*, replace: bool = False) -> None:
    """Register `${dtype:...}` and `${cuda_available:}`.

    Args:
        replace: Replace resolvers of the same names. Defaults to `False`.

    Raises:
        ImportError: If Torch is not installed.
        ValueError: If a name is taken and `replace` is `False`.
    """  # noqa: DOC503
    _import_torch()
    if not replace:
        for name in ("dtype", "cuda_available"):
            if OmegaConf.has_resolver(name):
                raise ValueError(f"Resolver `{name}` is already registered.")
    register_torch_dtype_resolver(replace=replace)
    register_cuda_available_resolver(replace=replace)


def _import_torch() -> Any:
    try:
        torch = importlib.import_module("torch")
    except ModuleNotFoundError as error:
        if error.name != "torch":
            raise
        raise ImportError(
            "Torch resolvers require PyTorch. Install torch for your platform."
        ) from error
    return torch


def _resolve_dtype(name: str) -> Any:
    torch = _import_torch()
    dtype = getattr(torch, name, None)
    if not isinstance(dtype, torch.dtype):
        raise ValueError(f"Invalid torch dtype `{name}`.")
    return dtype


def _cuda_available(_: Any = None) -> bool:
    return _import_torch().cuda.is_available()
