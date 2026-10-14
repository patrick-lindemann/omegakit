from omegaconf import OmegaConf

try:
    import numpy
except ImportError as error:
    raise ImportError(
        "Numpy resolvers require NumPy. Install it on your platform first."
    ) from error


def register_numpy_resolvers(*, replace: bool = False, use_cache: bool = True) -> None:
    """Register every NumPy resolver: `numpy.dtype`.

    Args:
        replace: Whether to replace a registered resolver of the same name. Defaults
            to `False`.
        use_cache: Whether to cache each result by its arguments. Defaults to `True`.
    """
    register_numpy_dtype_resolver(replace=replace, use_cache=use_cache)


def register_numpy_dtype_resolver(
    *, replace: bool = False, use_cache: bool = True
) -> None:
    """Register `${numpy.dtype:name}`, which resolves to `numpy.dtype(name)`.

    Args:
        replace: Whether to replace a registered resolver of the same name. Defaults
            to `False`.
        use_cache: Whether to cache each result by its arguments. Defaults to `True`.
    """
    OmegaConf.register_resolver(
        "numpy.dtype", numpy.dtype, replace=replace, use_cache=use_cache
    )
