from omegaconf import OmegaConf

from omegakit._core.utils.copy import copy_with_root


def test_copy_with_root_resolves_in_the_copied_root():
    config = OmegaConf.create({"width": 8, "models": [{"hidden": "${width}"}]})
    model_copy = copy_with_root(config.models[0])
    model_copy._get_root().width = 16
    assert model_copy.hidden == 16
    assert config.models[0].hidden == 8


def test_copy_with_root_of_a_root_is_a_copy():
    config = OmegaConf.create({"width": 8})
    config_copy = copy_with_root(config)
    config_copy.width = 16
    assert config.width == 8
