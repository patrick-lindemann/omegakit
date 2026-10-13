import copy
import pickle
from pathlib import Path

import pytest

from omegakit._core.errors import (
    ConfigFileNotFoundError,
    ConfigFilePermissionError,
    ConfigFileSyntaxError,
    ConfigIncludeError,
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
    SchemaDefinitionError,
    ValidationInterpolationError,
    ValidationMissingValueError,
)


@pytest.mark.parametrize(
    "error_type",
    [
        ConfigFileNotFoundError,
        ConfigFilePermissionError,
        ConfigFileSyntaxError,
        ConfigIncludeError,
        ConfigMergeError,
        ConfigOverrideError,
    ],
)
def test_error_of_loading_is_a_load_error(error_type: type[Exception]):
    assert issubclass(error_type, ConfigLoadError)
    assert not issubclass(error_type, ConfigValidationError)


@pytest.mark.parametrize(
    "error_type",
    [
        ValidationMissingValueError,
        ValidationInterpolationError,
        QualifiedNameSyntaxError,
        QualifiedNameNotFoundError,
        ConfigTargetError,
        ConfigSymbolError,
        ConfigSchemaError,
    ],
)
def test_error_of_validating_is_a_validation_error(error_type: type[Exception]):
    assert issubclass(error_type, ConfigValidationError)
    assert not issubclass(error_type, ConfigLoadError)


def test_wrong_schema_is_not_an_error_of_the_config():
    assert issubclass(SchemaDefinitionError, OmegaKitBaseException)
    assert not issubclass(SchemaDefinitionError, ConfigLoadError)
    assert not issubclass(SchemaDefinitionError, ConfigValidationError)


@pytest.mark.parametrize(
    ("error_type", "builtin_type"),
    [
        (ConfigFileNotFoundError, FileNotFoundError),
        (ConfigFilePermissionError, PermissionError),
        (QualifiedNameNotFoundError, ImportError),
    ],
)
def test_error_is_also_its_builtin_error(
    error_type: type[Exception], builtin_type: type[Exception]
):
    assert issubclass(error_type, builtin_type)


@pytest.mark.parametrize(
    "error_type",
    [ConfigTargetError, ConfigSymbolError, ConfigSchemaError, SchemaDefinitionError],
)
def test_error_is_no_builtin_type_error(error_type: type[Exception]):
    assert not issubclass(error_type, TypeError)


def test_error_without_a_place_shows_its_message():
    assert str(ConfigValidationError("The value is wrong.")) == "The value is wrong."


def test_error_shows_the_key_and_the_file():
    error = ConfigIncludeError("The include names no file.", "model.optimizer")
    assert "`model.optimizer`" in str(error)
    assert error.full_key == "model.optimizer"
    error.file_path = Path("configs/model.yaml")
    assert "configs/model.yaml" in str(error)


def test_error_at_the_root_says_so():
    assert "the root" in str(ConfigSchemaError("The value is wrong.", ""))


@pytest.mark.parametrize(
    "error_type",
    [ConfigSchemaError, ConfigFileNotFoundError, QualifiedNameNotFoundError],
)
def test_error_keeps_its_place_when_copied(error_type: type[OmegaKitBaseException]):
    error = error_type("The value is wrong.", "model", Path("model.yaml"))
    for copied_error in (copy.deepcopy(error), pickle.loads(pickle.dumps(error))):
        assert type(copied_error) is error_type
        assert str(copied_error) == str(error)
        assert copied_error.full_key == "model"
