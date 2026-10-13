from collections import defaultdict
from dataclasses import dataclass
from typing import Any

import pytest
from omegaconf import OmegaConf

from omegakit._core.errors import (
    ConfigOverrideError,
)
from omegakit._core.features.overrides import apply_overrides


@dataclass
class _Training:
    epochs: int = 10


def test_key_value_strings_set_nested_values():
    config = OmegaConf.create({"model": {"hidden": 32, "depth": 2}, "epochs": 10})
    config = apply_overrides(config, ["model.hidden=64", "epochs=50"])
    assert config == {"model": {"hidden": 64, "depth": 2}, "epochs": 50}


def test_key_value_strings_are_parsed_as_yaml():
    config = OmegaConf.create({})
    config = apply_overrides(config, ["epochs=50", "seeds=[0, 1]", "name=mlp", "flag"])
    assert config == {"epochs": 50, "seeds": [0, 1], "name": "mlp", "flag": None}


def test_key_value_strings_apply_in_order():
    config = OmegaConf.create({"model": {"hidden": 32, "depth": 2}})
    config = apply_overrides(config, ["model.hidden=64", "model=5", "model.width=8"])
    assert config == {"model": {"width": 8}}


@pytest.mark.parametrize("as_config", [False, True])
def test_a_mapping_merges_into_the_node_it_names(as_config: bool):
    config = OmegaConf.create({"optimizer": {"lr": 0.1, "momentum": 0.9}})
    overrides: Any = {"optimizer": {"lr": 0.001}}
    if as_config:
        overrides = OmegaConf.create(overrides)
    config = apply_overrides(config, overrides)
    assert config == {"optimizer": {"lr": 0.001, "momentum": 0.9}}


def test_an_override_may_hold_an_interpolation():
    config = OmegaConf.create({"width": 8, "hidden": 32})
    config = apply_overrides(config, ["hidden=${width}"])
    assert config.hidden == 8


def test_a_list_replaces_a_list_config():
    config = OmegaConf.create([1, 2, 3])
    config = apply_overrides(config, [9])
    assert config == [9]


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param(["model.hidden=64"], id="strings"),
        pytest.param({"model": {"hidden": 64}}, id="mapping"),
    ],
)
def test_the_default_returns_a_copy(overrides: Any):
    config = OmegaConf.create({"model": {"hidden": 32}})
    overridden_config = apply_overrides(config, overrides)
    assert overridden_config is not config
    assert overridden_config == {"model": {"hidden": 64}}
    assert config == {"model": {"hidden": 32}}


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param(["model.hidden=64"], id="strings"),
        pytest.param({"model": {"hidden": 64}}, id="mapping"),
    ],
)
def test_without_a_copy_the_config_itself_is_changed(overrides: Any):
    config = OmegaConf.create({"model": {"hidden": 32}})
    overridden_config = apply_overrides(config, overrides, copy=False)
    assert overridden_config is config
    assert config == {"model": {"hidden": 64}}


@pytest.mark.parametrize(
    "item",
    [
        pytest.param("a=[1", id="unclosed-list"),
        pytest.param("a=${", id="malformed-interpolation"),
        pytest.param("a=!!int x", id="invalid-tag-value"),
        pytest.param("[=1", id="malformed-key"),
    ],
)
def test_rejects_a_string_that_does_not_parse(item: str):
    config = OmegaConf.create({"a": 1})
    with pytest.raises(ConfigOverrideError) as error_info:
        apply_overrides(config, [item])
    assert item in str(error_info.value)


def test_rejects_a_list_item_that_is_not_a_string():
    config = OmegaConf.create({"a": 1})
    with pytest.raises(ConfigOverrideError):
        apply_overrides(config, [1])  # pyright: ignore[reportCallIssue, reportArgumentType]


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param("a=1", id="str"),
        pytest.param(None, id="none"),
        pytest.param(("a=1",), id="tuple"),
        pytest.param(OmegaConf.create(["a=1"]), id="list-config"),
    ],
)
def test_rejects_overrides_of_the_wrong_type(overrides: Any):
    config = OmegaConf.create({"a": 1})
    with pytest.raises(ConfigOverrideError):
        apply_overrides(config, overrides)


def test_rejects_a_mapping_for_a_list_config():
    config = OmegaConf.create([1, 2])
    with pytest.raises(ConfigOverrideError):
        apply_overrides(config, {"a": 1})  # pyright: ignore[reportCallIssue, reportArgumentType]


def test_rejects_a_new_key_on_a_struct_config():
    config = OmegaConf.create({"model": {"hidden": 32}})
    OmegaConf.set_struct(config, True)
    with pytest.raises(ConfigOverrideError, match=r"model\.width"):
        apply_overrides(config, ["model.width=8"])


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({"a": object()}, id="unsupported-value"),
        pytest.param(defaultdict(int, a=5), id="unsupported-mapping"),
    ],
)
def test_rejects_overrides_omegaconf_does_not_support(overrides: dict[str, Any]):
    config = OmegaConf.create({"a": 1})
    with pytest.raises(ConfigOverrideError):
        apply_overrides(config, overrides)


def test_rejects_a_value_of_the_wrong_type_for_a_typed_config():
    config = OmegaConf.structured(_Training)
    with pytest.raises(ConfigOverrideError, match="epochs"):
        apply_overrides(config, ["epochs=many"])


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param(["model.hidden=64", "model.width=[1"], id="strings"),
        pytest.param({"model": {"hidden": 64, "width": 8}}, id="mapping"),
    ],
)
def test_a_failure_leaves_the_config_unchanged(overrides: Any):
    config = OmegaConf.create({"model": {"hidden": 32}})
    OmegaConf.set_struct(config, True)
    with pytest.raises(ConfigOverrideError):
        apply_overrides(config, overrides)
    assert config == {"model": {"hidden": 32}}
