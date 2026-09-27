import importlib
from typing import Any

from omegaconf import OmegaConf

from omegakit.utils import register_resolver


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
        raise ValueError(f"Invalid torch dtype `{dtype_str}`.")
    return dtype


def register_torch_dtype_resolver(*, replace: bool = False) -> None:
    """Register `${dtype:float32}`, which gives the Torch dtype of that name.

    Args:
        replace: Replace a resolver named `dtype`. Defaults to `False`.

    Raises:
        ImportError: If Torch is not installed.
    """  # noqa: DOC502
    _import_torch()
    register_resolver("dtype", _resolve_dtype, replace=replace)


def register_cuda_available_resolver(*, replace: bool = False) -> None:
    """Register `${cuda_available:}`, which gives whether Torch can use CUDA.

    Args:
        replace: Replace a resolver named `cuda_available`. Defaults to `False`.

    Raises:
        ImportError: If Torch is not installed.
    """  # noqa: DOC502
    torch = _import_torch()
    register_resolver(
        "cuda_available",
        lambda _=None: torch.cuda.is_available(),
        replace=replace,
    )


def register_torch_resolvers(*, replace: bool = False) -> None:
    """Register `${dtype:...}` and `${cuda_available:}`.

    Neither is registered if either name is taken and `replace` is `False`.

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
