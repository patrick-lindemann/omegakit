import dataclasses
from collections.abc import Callable
from typing import Any

import pytest
from omegaconf import OmegaConf
from omegaconf.errors import (
    MissingMandatoryValue,
    OmegaConfBaseException,
    ValidationError,
)

from omegakit import (
    ConfigLoadError,
    Configurable,
    ConfigValidationError,
    OmegaKitBaseException,
    check_schema,
    generate_json_schema,
    instantiate,
    load_config,
    prepare,
    validate,
)


@dataclasses.dataclass
class Unsupported:
    tags: set[str]


class UsesUnsupported(Configurable[Unsupported]):
    def __init__(self, tags: set[str]) -> None:
        self.tags = tags


BAD_NODE = {"$class": "tests.helpers.Point", "$partial": "yes"}


def test_config_validation_error_is_an_omegaconf_validation_error():
    error = ConfigValidationError("message")
    assert isinstance(error, OmegaKitBaseException)
    assert isinstance(error, ValidationError)
    assert isinstance(error, OmegaConfBaseException)
    assert isinstance(error, ValueError)
    assert str(error) == "message"


def test_config_load_error_is_not_a_validation_error():
    error = ConfigLoadError("message")
    assert isinstance(error, OmegaKitBaseException)
    assert isinstance(error, ValueError)
    assert not isinstance(error, ValidationError)
    assert not isinstance(error, ConfigValidationError)


def test_base_exception_is_not_a_value_error():
    assert not issubclass(OmegaKitBaseException, ValueError)


@pytest.mark.parametrize(
    "call",
    [
        lambda path: load_config(path),
        lambda path: validate(BAD_NODE),
        lambda path: instantiate(BAD_NODE),
        lambda path: prepare(BAD_NODE),
        lambda path: instantiate({"$class": "tests.helpers.Point"}, overrides=["x=["]),
        lambda path: check_schema(UsesUnsupported),
        lambda path: generate_json_schema(Unsupported),
    ],
    ids=[
        "load_config",
        "validate",
        "instantiate",
        "prepare",
        "overrides",
        "check_schema",
        "generate_json_schema",
    ],
)
def test_omegaconf_handler_catches_errors_of_every_public_function(
    write_yaml, call: Callable[[Any], Any]
):
    path = write_yaml("c.yaml", "a: [1\n")
    with pytest.raises(OmegaConfBaseException) as info:
        call(path)
    assert isinstance(info.value, OmegaKitBaseException)


@pytest.mark.parametrize("overrides", [["x=[1"], {"x": object()}])
def test_override_errors_are_load_errors_in_every_function(write_yaml, overrides):
    path = write_yaml("c.yaml", "x: 1\n")
    with pytest.raises(ConfigLoadError, match="override"):
        load_config(path, overrides=overrides)
    for build in (instantiate, prepare):
        with pytest.raises(ConfigLoadError, match="override"):
            build({"$class": "tests.helpers.Point", "x": 1}, overrides=overrides)


def test_omegakit_handler_lets_omegaconf_errors_through():
    config = OmegaConf.create({"a": "???"})
    with pytest.raises(MissingMandatoryValue) as info:
        _ = config.a
    assert not isinstance(info.value, OmegaKitBaseException)


def test_nested_import_failure_has_one_prefix_per_import(write_yaml):
    path = write_yaml("a.yaml", "n: ~import b.yaml\n")
    b = write_yaml("b.yaml", "m: ~import c.yaml\n")
    c = write_yaml("c.yaml", "hello\n")
    with pytest.raises(ConfigLoadError) as info:
        load_config(path)
    assert str(info.value) == (
        f"Cannot import `~import c.yaml` in `{b}`: Cannot load `{c}`: it holds a "
        "single value, not a mapping or a list."
    )


def test_base_failure_has_no_load_prefix(write_yaml):
    with pytest.raises(ConfigLoadError) as info:
        load_config(write_yaml("c.yaml", "m:\n  $base: 3\n"))
    assert str(info.value) == (
        "`$base` in `m` is not a dictionary or a list of dictionaries."
    )


def test_base_resolution_failure_has_one_prefix(write_yaml):
    with pytest.raises(ConfigLoadError) as info:
        load_config(write_yaml("c.yaml", "m:\n  $base: ${nope}\n"))
    assert str(info.value) == (
        "Cannot resolve `m.$base`: Interpolation key 'nope' not found"
    )
