from typing import Any

from omegaconf import OmegaConf

try:
    import torch
except ImportError as error:
    raise ImportError(
        "Torch resolvers require PyTorch. Install it on your platform first."
    ) from error


def register_torch_resolvers(*, replace: bool = False, use_cache: bool = True) -> None:
    """Register `torch.has_cuda`, `torch.device` and `torch.dtype`.

    Args:
        replace: Whether to replace a registered resolver of the same name. Defaults
            to `False`.
        use_cache: Whether to cache each result by its arguments. Defaults to `True`.
    """
    register_torch_cuda_resolver(replace=replace, use_cache=use_cache)
    register_torch_device_resolver(replace=replace, use_cache=use_cache)
    register_torch_dtype_resolver(replace=replace, use_cache=use_cache)


def register_torch_cuda_resolver(
    *, replace: bool = False, use_cache: bool = True
) -> None:
    """Register `${torch.has_cuda:}`, which resolves to whether CUDA is available.

    Args:
        replace: Whether to replace a registered resolver of the same name. Defaults
            to `False`.
        use_cache: Whether to cache each result by its arguments. Defaults to `True`.
    """
    OmegaConf.register_resolver(
        "torch.has_cuda",
        lambda: torch.cuda.is_available(),
        replace=replace,
        use_cache=use_cache,
    )


def register_torch_device_resolver(
    *, replace: bool = False, use_cache: bool = True
) -> None:
    """Register `${torch.device:name}`, which resolves to `torch.device(name)`.

    Args:
        replace: Whether to replace a registered resolver of the same name. Defaults
            to `False`.
        use_cache: Whether to cache each result by its arguments. Defaults to `True`.
    """
    OmegaConf.register_resolver(
        "torch.device", _resolve_device, replace=replace, use_cache=use_cache
    )


def register_torch_dtype_resolver(
    *, replace: bool = False, use_cache: bool = True
) -> None:
    """Register `${torch.dtype:name}`, which resolves to the dtype `torch.<name>`.

    Args:
        replace: Whether to replace a registered resolver of the same name. Defaults
            to `False`.
        use_cache: Whether to cache each result by its arguments. Defaults to `True`.
    """
    OmegaConf.register_resolver(
        "torch.dtype", _resolve_dtype, replace=replace, use_cache=use_cache
    )


# OmegaConf cannot read the signature of `torch.device` itself
def _resolve_device(name: str) -> Any:
    return torch.device(name)


def _resolve_dtype(name: str) -> Any:
    dtype = getattr(torch, name, None)
    if not isinstance(dtype, torch.dtype):
        raise ValueError(f"Invalid torch dtype `{name}`.")
    return dtype
