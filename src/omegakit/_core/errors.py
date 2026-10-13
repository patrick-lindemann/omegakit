from omegaconf.errors import (
    InterpolationResolutionError,
    MissingMandatoryValue,
)


class OmegaKitBaseException(Exception):
    pass


class ConfigLoadError(OmegaKitBaseException):
    pass


class ConfigValidationError(OmegaKitBaseException):
    pass


class ConfigFileNotFoundError(ConfigLoadError, FileNotFoundError):
    pass


class ConfigFilePermissionError(ConfigLoadError, PermissionError):
    pass


class ConfigFileSyntaxError(ConfigLoadError, ValueError):
    pass


class QualifiedNameSyntaxError(ConfigValidationError, ValueError):
    pass


class QualifiedNameNotFoundError(ConfigValidationError, ImportError):
    pass


class ConfigMergeError(ConfigLoadError):
    pass


class ConfigIncludeError(ConfigLoadError):
    pass


class IncludeRootError(ConfigIncludeError):
    pass


class ConfigOverrideError(ConfigLoadError):
    pass


class ValidationInterpolationError(ConfigValidationError, InterpolationResolutionError):
    pass


class ValidationMissingValueError(ConfigValidationError, MissingMandatoryValue):
    pass


class ConfigTargetError(ConfigValidationError):
    pass


class ConfigSymbolError(ConfigValidationError):
    pass


class ConfigSchemaError(ConfigValidationError):
    pass


class SchemaDefinitionError(OmegaKitBaseException, TypeError):
    pass
