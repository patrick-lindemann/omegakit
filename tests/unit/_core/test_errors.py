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
