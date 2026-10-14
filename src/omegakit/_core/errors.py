from pathlib import Path
from typing import override


class OmegaKitBaseException(Exception):
    """An error of omegakit, whose message names the place of the mistake."""

    message: str
    full_key: str | None
    file_path: Path | None

    def __init__(
        self, message: str, full_key: str | None = None, file_path: Path | None = None
    ) -> None:
        """Initialize the error.

        A `full_key` of `""` names the root.

        Args:
            message: What is wrong, as a full sentence.
            full_key: The key of the node at fault. Defaults to `None`, in which case
                the error concerns no node.
            file_path: The config file at fault. Defaults to `None`, in which case it is
                unknown.
        """
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
    """An error in loading a config: reading, including, merging or overriding."""


class ConfigValidationError(OmegaKitBaseException):
    """An error in checking a config or in building objects from it."""


class ConfigFileNotFoundError(ConfigLoadError, FileNotFoundError):
    """An error for a config file that does not exist."""


class ConfigFilePermissionError(ConfigLoadError, PermissionError):
    """An error for a config file that may not be read."""


class ConfigFileSyntaxError(ConfigLoadError):
    """An error for a config file that is no valid YAML or whose root is no mapping."""


class QualifiedNameSyntaxError(ConfigValidationError):
    """An error for an import path that is not of the form `package.module.Name`."""


class QualifiedNameNotFoundError(ConfigValidationError, ImportError):
    """An error for an import path whose module or attribute does not exist."""


class ConfigMergeError(ConfigLoadError):
    """An error for a `$base` or `$each` that cannot be merged."""


class ConfigIncludeError(ConfigLoadError):
    """An error for an `~include` that cannot be resolved."""


class IncludeRootError(ConfigIncludeError):
    """An error for an `~include` of a file outside the include root."""


class ConfigOverrideError(ConfigLoadError):
    """An error for an override that cannot be parsed or applied."""


class ValidationInterpolationError(ConfigValidationError):
    """An error for an interpolation that cannot be resolved in a check."""


class ValidationMissingValueError(ConfigValidationError):
    """An error for a value that is `???` while a config is checked."""


class ConfigTargetError(ConfigValidationError):
    """An error for a missing or invalid `$target`, `$args` or `$partial`."""


class ConfigSymbolError(ConfigValidationError):
    """An error for an invalid `$symbol`."""


class ConfigSchemaError(ConfigValidationError):
    """An error for a config value or built object that does not match its schema."""


class SchemaDefinitionError(OmegaKitBaseException):
    """An error for a schema that cannot be used to check a config."""
