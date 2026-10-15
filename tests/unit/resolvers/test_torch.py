import warnings

import pytest
import torch
from omegaconf import OmegaConf
from omegaconf.errors import InterpolationResolutionError

from omegakit.resolvers.torch import register_torch_resolvers

pytestmark = pytest.mark.resolvers


def test_resolvers_give_torch_objects():
    register_torch_resolvers(replace=True)
    config = OmegaConf.create(
        {
            "device": "${torch.device:cpu}",
            "dtype": "${torch.dtype:float32}",
            "has_cuda": "${torch.has_cuda:}",
        }
    )
    assert config.device == torch.device("cpu")
    assert config.dtype is torch.float32
    assert config.has_cuda is torch.cuda.is_available()


def test_registering_raises_no_warning():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        register_torch_resolvers(replace=True)


def test_unknown_dtype_is_rejected():
    register_torch_resolvers(replace=True)
    config = OmegaConf.create({"dtype": "${torch.dtype:float33}"})
    with pytest.raises(InterpolationResolutionError, match="float33"):
        _ = config.dtype
