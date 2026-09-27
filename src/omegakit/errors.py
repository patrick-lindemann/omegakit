from omegaconf.errors import OmegaConfBaseException, ValidationError


class OmegaKitBaseException(OmegaConfBaseException):
    """The base of every error that omegakit raises about a config or a schema."""

    __module__ = "omegakit"


class ConfigLoadError(OmegaKitBaseException, ValueError):
    """A config file, an import, a `$base`, a `$defaults` or an override is invalid."""

    __module__ = "omegakit"


class ConfigValidationError(OmegaKitBaseException, ValidationError):
    """A config does not match the schema of the class it builds."""

    __module__ = "omegakit"
