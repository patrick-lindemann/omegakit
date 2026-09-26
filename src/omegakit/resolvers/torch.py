"""Optional Torch resolvers. Torch is needed only when registering or resolving."""

import importlib
from typing import Any

from omegaconf import OmegaConf


def _import_torch() -> Any:
    try:
        torch = importlib.import_module("torch")
    except ModuleNotFoundError as error:
        if error.name != "torch":
            raise
        raise ImportError(
            "Torch resolvers require PyTorch. Install torch for your platform "
            "before calling register_torch_resolvers()."
        ) from error
    return torch


def _resolve_dtype(dtype_str: str) -> Any:
    torch = _import_torch()
    dtype = getattr(torch, dtype_str, None)
    if not isinstance(dtype, torch.dtype):
        raise ValueError(f"Invalid torch dtype: {dtype_str}")
    return dtype


def register_torch_dtype_resolver(*, replace: bool = False) -> None:
    """Register `${dtype:float32}`; require an existing Torch installation."""
    _import_torch()
    OmegaConf.register_new_resolver(
        "dtype", _resolve_dtype, replace=replace, use_cache=True
    )


def register_cuda_available_resolver(*, replace: bool = False) -> None:
    """Register `${cuda_available:}`; require an existing Torch installation."""
    torch = _import_torch()
    OmegaConf.register_new_resolver(
        "cuda_available",
        lambda _=None: torch.cuda.is_available(),
        replace=replace,
        use_cache=True,
    )


def register_torch_resolvers(*, replace: bool = False) -> None:
    """Register both Torch resolvers, without overwriting names by default."""
    _import_torch()
    if not replace:
        for name in ("dtype", "cuda_available"):
            if OmegaConf.has_resolver(name):
                raise ValueError(f"Resolver '{name}' is already registered")
    register_torch_dtype_resolver(replace=replace)
    register_cuda_available_resolver(replace=replace)
