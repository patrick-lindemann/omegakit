import warnings

import numpy
import pytest
from omegaconf import OmegaConf
from omegaconf.errors import InterpolationResolutionError

from omegakit.resolvers.numpy import register_numpy_resolvers

pytestmark = pytest.mark.resolvers


def test_resolver_gives_a_dtype():
    register_numpy_resolvers(replace=True)
    config = OmegaConf.create({"dtype": "${numpy.dtype:float32}"})
    assert config.dtype == numpy.dtype("float32")


def test_registration_does_not_warn():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        register_numpy_resolvers(replace=True)


def test_unknown_dtype_is_rejected():
    register_numpy_resolvers(replace=True)
    config = OmegaConf.create({"dtype": "${numpy.dtype:float33}"})
    with pytest.raises(InterpolationResolutionError, match="float33"):
        _ = config.dtype
