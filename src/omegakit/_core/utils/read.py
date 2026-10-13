from typing import Any

from omegaconf import DictConfig, ListConfig, TupleConfig
from omegaconf.errors import InterpolationResolutionError, MissingMandatoryValue

from omegakit._core.errors import (
    ValidationInterpolationError,
    ValidationMissingValueError,
)

from .describe import describe_error


def read_value(parent: DictConfig | ListConfig | TupleConfig, key: Any) -> Any:
    try:
        # Resolves an interpolation, as in `$target: ${model}`
        return parent[key]
    except MissingMandatoryValue:
        # The error of OmegaConf says the same and would only lengthen the traceback
        raise ValidationMissingValueError(
            "The value is `???`. Set it in the config or with an override.",
            parent._get_full_key(key),
        ) from None
    except InterpolationResolutionError as error:
        raise ValidationInterpolationError(
            f"Cannot resolve the value: {describe_error(error)}",
            parent._get_full_key(key),
        ) from error
