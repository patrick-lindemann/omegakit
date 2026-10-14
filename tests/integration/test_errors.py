from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from omegaconf import OmegaConf

from omegakit._core.errors import (
    ConfigFileNotFoundError,
    ConfigFileSyntaxError,
    ConfigLoadError,
    ConfigMergeError,
    ConfigOverrideError,
    ConfigSchemaError,
    ConfigSymbolError,
    ConfigTargetError,
    ConfigValidationError,
    OmegaKitBaseException,
    QualifiedNameNotFoundError,
    QualifiedNameSyntaxError,
    ValidationInterpolationError,
    ValidationMissingValueError,
)
from omegakit._core.load import load_config
from omegakit._core.validate import validate


@pytest.mark.parametrize(
    ("content", "overrides", "error_type", "full_key"),
    [
        ("model: [1", None, ConfigFileSyntaxError, None),
        ("- 1\n- 2\n", None, ConfigFileSyntaxError, None),
        ("model: ~include nope.yaml", None, ConfigFileNotFoundError, "model"),
        ("model: {$base: 3}", None, ConfigMergeError, "model"),
        ("data: {$each: 3, train: {}}", None, ConfigMergeError, "data"),
        ("seed: 1", ["seed"], ConfigOverrideError, None),
    ],
)
def test_mistake_in_loading_is_a_load_error(
    tmp_path: Path,
    content: str,
    overrides: list[str] | None,
    error_type: type[OmegaKitBaseException],
    full_key: str | None,
):
    path = tmp_path / "config.yaml"
    path.write_text(content)
    with pytest.raises(ConfigLoadError) as error_info:
        load_config(path, overrides)
    assert type(error_info.value) is error_type
    assert error_info.value.full_key == full_key
    if full_key is not None:
        assert f"`{full_key}`" in str(error_info.value)


def test_missing_file_is_a_load_error(tmp_path: Path):
    with pytest.raises(ConfigLoadError) as error_info:
        load_config(tmp_path / "nope.yaml")
    assert type(error_info.value) is ConfigFileNotFoundError


@pytest.mark.parametrize(
    ("model", "error_type", "full_key"),
    [
        ({"lr": "???"}, ValidationMissingValueError, "model.lr"),
        ({"lr": "${nope}"}, ValidationInterpolationError, "model.lr"),
        ({"$target": "tests.targets.Nope"}, QualifiedNameNotFoundError, "model"),
        ({"$target": "nomodule"}, QualifiedNameSyntaxError, "model"),
        ({"$target": "math.pi"}, ConfigTargetError, "model"),
        ({"$symbol": "math.pi", "digits": 2}, ConfigSymbolError, "model"),
        (
            {"$target": "tests.targets.Model", "dpeth": 1},
            ConfigSchemaError,
            "model",
        ),
        ({"$foo": 1}, ConfigValidationError, "model"),
    ],
)
def test_mistake_in_the_config_is_a_validation_error(
    targets: ModuleType,
    model: dict[str, Any],
    error_type: type[OmegaKitBaseException],
    full_key: str,
):
    config = OmegaConf.create({"model": model})
    with pytest.raises(ConfigValidationError) as error_info:
        validate(config)
    assert type(error_info.value) is error_type
    assert error_info.value.full_key == full_key
    assert f"`{full_key}`" in str(error_info.value)
    assert targets.CALLS == []
