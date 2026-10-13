from omegaconf.errors import (
    ConfigKeyError,
    InterpolationResolutionError,
    MissingMandatoryValue,
    ValidationError,
)


class OmegaKitBaseException(Exception):
    pass


class ConfigFileNotFoundError(OmegaKitBaseException, FileNotFoundError):
    pass


class ConfigFilePermissionError(OmegaKitBaseException, PermissionError):
    pass


class ConfigSyntaxError(OmegaKitBaseException, ValueError):
    pass


class QualifiedNameSyntaxError(OmegaKitBaseException, ValueError):
    pass


class QualifiedNameNotFoundError(OmegaKitBaseException, ImportError):
    pass


class ConfigMergeError(OmegaKitBaseException):
    pass


class MergeReferenceError(ConfigMergeError, InterpolationResolutionError):
    pass


class MergeCycleError(ConfigMergeError):
    pass


class ConfigLoadError(OmegaKitBaseException):
    pass


class LoadTypeError(ConfigLoadError, TypeError):
    pass


class ConfigIncludeError(OmegaKitBaseException):
    pass


class IncludeSyntaxError(ConfigIncludeError, ValueError):
    pass


class IncludeInterpolationError(ConfigIncludeError, InterpolationResolutionError):
    pass


class IncludeTypeError(ConfigIncludeError, TypeError):
    pass


class IncludeCycleError(ConfigIncludeError):
    pass


class IncludeNodeNotFoundError(ConfigIncludeError):
    pass


class IncludeRootError(ConfigIncludeError):
    pass


class IncludeMissingValueError(ConfigIncludeError, MissingMandatoryValue):
    pass


class ConfigInheritanceError(OmegaKitBaseException):
    pass


class BaseTypeError(ConfigInheritanceError, TypeError):
    pass


class ConfigEachError(OmegaKitBaseException):
    pass


class EachTypeError(ConfigEachError, TypeError):
    pass


class ConfigOverrideError(OmegaKitBaseException):
    pass


class OverrideSyntaxError(ConfigOverrideError, ValueError):
    pass


class OverrideTypeError(ConfigOverrideError, TypeError):
    pass


class OverrideMergeError(ConfigOverrideError):
    pass


class ConfigValidationError(OmegaKitBaseException):
    pass


class ValidationSyntaxError(ConfigValidationError, ValueError):
    pass


class ValidationInterpolationError(ConfigValidationError, InterpolationResolutionError):
    pass


class ValidationMissingValueError(ConfigValidationError, MissingMandatoryValue):
    pass


class ValidationCycleError(ConfigValidationError):
    pass


class ConfigTargetError(OmegaKitBaseException):
    pass


class TargetSyntaxError(ConfigTargetError, ValueError):
    pass


class TargetTypeError(ConfigTargetError, TypeError):
    pass


class TargetInterpolationError(ConfigTargetError, InterpolationResolutionError):
    pass


class TargetMissingValueError(ConfigTargetError, MissingMandatoryValue):
    pass


class ConfigSymbolError(OmegaKitBaseException):
    pass


class SymbolSyntaxError(ConfigSymbolError, ValueError):
    pass


class SymbolTypeError(ConfigSymbolError, TypeError):
    pass


class SymbolInterpolationError(ConfigSymbolError, InterpolationResolutionError):
    pass


class SymbolMissingValueError(ConfigSymbolError, MissingMandatoryValue):
    pass


class ConfigSchemaError(OmegaKitBaseException):
    pass


class SchemaDefinitionError(ConfigSchemaError, TypeError):
    pass


class SchemaKeyError(ConfigSchemaError, ConfigKeyError):
    pass


class SchemaMissingValueError(ConfigSchemaError, MissingMandatoryValue):
    pass


class SchemaValueError(ConfigSchemaError, ValidationError):
    pass


class SchemaTypeError(ConfigSchemaError, ValidationError):
    pass
