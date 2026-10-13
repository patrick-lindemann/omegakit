from omegaconf.errors import (
    ConfigKeyError,
    InterpolationResolutionError,
    MissingMandatoryValue,
    ValidationError,
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


class MergeReferenceError(ConfigMergeError, InterpolationResolutionError):
    pass


class MergeCycleError(ConfigMergeError):
    pass


class ConfigIncludeError(ConfigLoadError):
    pass


class IncludeRootError(ConfigIncludeError):
    pass


class BaseTypeError(ConfigMergeError, TypeError):
    pass


class EachTypeError(ConfigMergeError, TypeError):
    pass


class ConfigOverrideError(ConfigLoadError):
    pass


class OverrideSyntaxError(ConfigOverrideError, ValueError):
    pass


class OverrideTypeError(ConfigOverrideError, TypeError):
    pass


class OverrideMergeError(ConfigOverrideError):
    pass


class ValidationSyntaxError(ConfigValidationError, ValueError):
    pass


class ValidationInterpolationError(ConfigValidationError, InterpolationResolutionError):
    pass


class ValidationMissingValueError(ConfigValidationError, MissingMandatoryValue):
    pass


class ValidationCycleError(ConfigValidationError):
    pass


class ConfigTargetError(ConfigValidationError):
    pass


class TargetSyntaxError(ConfigTargetError, ValueError):
    pass


class TargetTypeError(ConfigTargetError, TypeError):
    pass


class TargetInterpolationError(ConfigTargetError, InterpolationResolutionError):
    pass


class TargetMissingValueError(ConfigTargetError, MissingMandatoryValue):
    pass


class ConfigSymbolError(ConfigValidationError):
    pass


class SymbolSyntaxError(ConfigSymbolError, ValueError):
    pass


class SymbolTypeError(ConfigSymbolError, TypeError):
    pass


class SymbolInterpolationError(ConfigSymbolError, InterpolationResolutionError):
    pass


class SymbolMissingValueError(ConfigSymbolError, MissingMandatoryValue):
    pass


class ConfigSchemaError(ConfigValidationError):
    pass


class SchemaDefinitionError(OmegaKitBaseException, TypeError):
    pass


class SchemaKeyError(ConfigSchemaError, ConfigKeyError):
    pass


class SchemaMissingValueError(ConfigSchemaError, MissingMandatoryValue):
    pass


class SchemaValueError(ConfigSchemaError, ValidationError):
    pass


class SchemaTypeError(ConfigSchemaError, ValidationError):
    pass
