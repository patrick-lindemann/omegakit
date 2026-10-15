from typing import Any

import pytest
from omegaconf import OmegaConf
from omegaconf.errors import ConfigTypeError, ReadonlyConfigError

from omegakit._core.features.meta import remove_meta


def test_removes_meta_from_every_mapping():
    config = OmegaConf.create(
        {
            "$meta": {"title": "Wide MLP"},
            "model": {"$meta": {"description": "Wider"}, "hidden": 256},
            "stages": [{"$meta": "first", "epochs": 1}, [{"$meta": "inner"}]],
        }
    )
    config = remove_meta(config)
    assert config == {
        "model": {"hidden": 256},
        "stages": [{"epochs": 1}, [{}]],
    }


def test_removes_meta_from_a_list_config():
    config = OmegaConf.create([{"$meta": 1, "a": 2}])
    config = remove_meta(config)
    assert config == [{"a": 2}]


@pytest.mark.parametrize(
    "meta",
    [
        pytest.param("???", id="missing"),
        pytest.param("${nope}", id="failing-interpolation"),
        pytest.param(None, id="null"),
        pytest.param({"$meta": 1}, id="nested-meta"),
    ],
)
def test_removes_meta_whatever_it_holds(meta: Any):
    config = OmegaConf.create({"model": {"$meta": meta, "hidden": 256}})
    config = remove_meta(config)
    assert config == {"model": {"hidden": 256}}


def test_keeps_a_config_without_meta_unchanged():
    config = OmegaConf.create({"seed": 0, "lr": "${seed}", "data": "???"})
    config = remove_meta(config)
    assert OmegaConf.to_container(config) == {
        "seed": 0,
        "lr": "${seed}",
        "data": "???",
    }


def test_the_default_returns_a_copy():
    content = {"model": {"$meta": "note", "hidden": 256}}
    config = OmegaConf.create(content)
    stripped_config = remove_meta(config)
    assert stripped_config is not config
    assert stripped_config == {"model": {"hidden": 256}}
    assert config == content


def test_without_a_copy_the_config_itself_is_changed():
    config = OmegaConf.create({"model": {"$meta": "note", "hidden": 256}})
    stripped_config = remove_meta(config, copy=False)
    assert stripped_config is config
    assert config == {"model": {"hidden": 256}}


def test_a_read_only_config_keeps_its_meta():
    config = OmegaConf.create({"model": {"$meta": "note", "hidden": 256}})
    OmegaConf.set_readonly(config, True)
    with pytest.raises(ReadonlyConfigError):
        remove_meta(config)
    assert config.model["$meta"] == "note"


def test_a_struct_config_keeps_its_meta():
    config = OmegaConf.create({"model": {"$meta": "note", "hidden": 256}})
    OmegaConf.set_struct(config, True)
    with pytest.raises(ConfigTypeError):
        remove_meta(config)
    assert config.model["$meta"] == "note"
