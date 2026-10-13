from typing import Any

from omegaconf import OmegaConf

try:
    import torch
except ImportError as error:
    raise ImportError(
        "Torch resolvers require PyTorch. Install it on your platform first."
    ) from error


def register_torch_cuda_resolver(
    *, replace: bool = False, use_cache: bool = True
) -> None:
    """__summary__"""
    OmegaConf.register_resolver(
        "torch.has_cuda",
        lambda: torch.cuda.is_available(),
        replace=replace,
        use_cache=use_cache,
    )


def register_torch_device_resolver(
    *, replace: bool = False, use_cache: bool = True
) -> None:
    """__summary__"""
    OmegaConf.register_resolver(
        "torch.device", torch.device, replace=replace, use_cache=use_cache
    )


def register_torch_dtype_resolver(
    *, replace: bool = False, use_cache: bool = True
) -> None:
    """__summary__"""
    OmegaConf.register_resolver(
        "torch.dtype", _resolve_dtype, replace=replace, use_cache=use_cache
    )


def _resolve_dtype(name: str) -> Any:
    dtype = getattr(torch, name, None)
    if not isinstance(dtype, torch.dtype):
        raise ValueError(f"Invalid torch dtype `{name}`.")
    return dtype
