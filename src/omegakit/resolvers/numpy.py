from omegaconf import OmegaConf

try:
    import numpy
except ImportError as error:
    raise ImportError(
        "Numpy resolvers require NumPy. Install it on your platform first."
    ) from error


def register_numpy_resolvers(*, replace: bool = False, use_cache: bool = True) -> None:
    """__summary__"""
    register_numpy_dtype_resolver(replace=replace, use_cache=use_cache)


def register_numpy_dtype_resolver(
    *, replace: bool = False, use_cache: bool = True
) -> None:
    """__summary__"""
    OmegaConf.register_resolver(
        "numpy.dtype", numpy.dtype, replace=replace, use_cache=use_cache
    )
