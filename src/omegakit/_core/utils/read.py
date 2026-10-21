from typing import Any

from omegaconf import DictConfig, ListConfig, TupleConfig
from omegaconf.errors import (
    InterpolationKeyError,
    InterpolationResolutionError,
    InterpolationToMissingValueError,
    MissingMandatoryValue,
)

from omegakit._core.errors import (
    ValidationInterpolationError,
    ValidationMissingValueError,
)

from .describe import describe_error

# What `read_value` gives for a missing value when it is allowed
MISSING_VALUE: Any = object()


def read_value(
    parent: DictConfig | ListConfig | TupleConfig, key: Any, allow_missing: bool = False
) -> Any:
    """Read and resolve a value of a config.

    Args:
        parent: The config that holds the value.
        key: The key of the value.
        allow_missing: Whether to accept a `???` and an interpolation to a missing or
            unknown key. Defaults to `False`.

    Returns:
        The value, or `MISSING_VALUE` for a missing value that is allowed.

    Raises:
        ValidationMissingValueError: If the value is `???` and not allowed.
        ValidationInterpolationError: If the value cannot be resolved.
    """
    try:
        # Resolves an interpolation, as in `$target: ${model}`
        return parent[key]
    except MissingMandatoryValue:
        if allow_missing:
            return MISSING_VALUE
        # The error of OmegaConf says the same and would only lengthen the traceback
        raise ValidationMissingValueError(
            "The value is `???`. Set it in the config or with an override.",
            parent._get_full_key(key),
        ) from None
    except InterpolationResolutionError as error:
        # An interpolation to a missing or unknown key
        if allow_missing and isinstance(
            error, (InterpolationToMissingValueError, InterpolationKeyError)
        ):
            return MISSING_VALUE
        raise ValidationInterpolationError(
            f"Cannot resolve the value: {describe_error(error)}",
            parent._get_full_key(key),
        ) from error
