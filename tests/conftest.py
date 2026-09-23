import pytest
from omegaconf import OmegaConf


@pytest.fixture(autouse=True)
def clear_resolvers():
    OmegaConf.clear_resolvers()
    yield
    OmegaConf.clear_resolvers()
