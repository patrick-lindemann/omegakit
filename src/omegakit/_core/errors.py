from pathlib import Path
from typing import override


class OmegaKitBaseException(Exception):
    message: str
    full_key: str | None
    file_path: Path | None

    def __init__(
        self, message: str, full_key: str | None = None, file_path: Path | None = None
    ) -> None:
        super().__init__(message)
        self.message = message
        self.full_key = full_key
        self.file_path = file_path

    @override
    def __str__(self) -> str:
        places = []
        if self.full_key is not None:
            places.append(f"at `{self.full_key}`" if self.full_key else "at the root")
        if self.file_path is not None:
            places.append(f"in `{self.file_path}`")
        if not places:
            return self.message
        return f"{self.message} ({' '.join(places)})"


class ConfigLoadError(OmegaKitBaseException):
    pass


class ConfigValidationError(OmegaKitBaseException):
    pass


class ConfigFileNotFoundError(ConfigLoadError, FileNotFoundError):
    pass


class ConfigFilePermissionError(ConfigLoadError, PermissionError):
    pass


class ConfigFileSyntaxError(ConfigLoadError):
    pass


class QualifiedNameSyntaxError(ConfigValidationError):
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


class ValidationInterpolationError(ConfigValidationError):
    pass


class ValidationMissingValueError(ConfigValidationError):
    pass


class ConfigTargetError(ConfigValidationError):
    pass


class ConfigSymbolError(ConfigValidationError):
    pass


class ConfigSchemaError(ConfigValidationError):
    pass


class SchemaDefinitionError(OmegaKitBaseException):
    pass
