import pytest
import yaml
from omegaconf import OmegaConf

from omegakit._core.utils.describe import describe_error, describe_node, get_full_key


def test_node_is_named_by_its_full_key():
    config = OmegaConf.create({"models": [{"depth": 2}]})
    node = config.models[0]
    assert get_full_key(node) == "models[0]"
    assert describe_node(node) == "`models[0]`"


def test_root_has_an_empty_key_and_a_name():
    config = OmegaConf.create({"seed": 0})
    assert get_full_key(config) == ""
    assert describe_node(config) == "the root"


def test_error_is_described_by_its_first_line():
    assert describe_error(ValueError("Wrong value.\nMore detail.")) == "Wrong value."


def test_error_without_a_message_is_described_by_its_type():
    assert describe_error(KeyError()) == "KeyError"


def test_yaml_error_is_described_with_its_position():
    with pytest.raises(yaml.MarkedYAMLError) as error_info:
        yaml.safe_load("model: [1")
    description = describe_error(error_info.value)
    assert "line" in description
    assert "column" in description
    assert "\n" not in description
