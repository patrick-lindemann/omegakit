from typing import Any

import pytest
from omegaconf import DictConfig, ListConfig, OmegaConf, TupleConfig

from omegakit._core.config import cast_config


@pytest.mark.parametrize(
    ("value", "config_type"),
    [
        ({"depth": 2, "layers": [1, 2]}, DictConfig),
        ([1, {"depth": 2}], ListConfig),
        ((1, 2), TupleConfig),
    ],
)
def test_plain_container_becomes_its_config(value: Any, config_type: type):
    config = cast_config(value)
    assert type(config) is config_type
    assert OmegaConf.to_container(config) == value


def test_config_stays_the_same_object():
    config = OmegaConf.create({"depth": 2})
    assert cast_config(config) is config
