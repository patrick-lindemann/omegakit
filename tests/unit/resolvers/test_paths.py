import warnings
from pathlib import Path

import pytest
from omegaconf import OmegaConf
from omegaconf.errors import InterpolationResolutionError

from omegakit.resolvers.paths import register_paths_resolver

pytestmark = pytest.mark.resolvers


def test_resolver_gives_the_path_of_a_name():
    register_paths_resolver({"data": Path("/srv/data"), "runs": "runs"}, replace=True)
    config = OmegaConf.create({"train": "${paths:data}/train", "out": "${paths:runs}"})
    assert config.train == "/srv/data/train"
    assert config.out == "runs"


def test_registration_does_not_warn():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        register_paths_resolver({"data": "/srv/data"}, replace=True)


def test_unknown_name_is_rejected():
    register_paths_resolver({"data": "/srv/data"}, replace=True)
    config = OmegaConf.create({"train": "${paths:dta}"})
    with pytest.raises(InterpolationResolutionError, match="dta"):
        _ = config.train
