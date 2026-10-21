import os
from pathlib import Path

from omegaconf import DictConfig, ListConfig, OmegaConf

from omegakit._core.errors import (
    ConfigFileNotFoundError,
    ConfigFilePermissionError,
    ConfigFileSyntaxError,
)

from .describe import describe_error


def load_yaml(file_path: Path) -> DictConfig | ListConfig:  # noqa: DOC503
    """Load a YAML file as a config, without assembling it.

    Args:
        file_path: The file.

    Returns:
        The config.

    Raises:
        ConfigFileNotFoundError: If `file_path` is not a file.
        ConfigFilePermissionError: If the file may not be read.
        OSError: If reading the file fails otherwise.
        ConfigFileSyntaxError: If the file cannot be parsed.
    """
    if not os.path.isfile(file_path):
        not_found_error = ConfigFileNotFoundError(f"`{file_path}` is not a file.")
        # Handlers of a builtin `OSError` read the file from `filename`
        not_found_error.filename = str(file_path)
        raise not_found_error
    try:
        return OmegaConf.load(file_path)
    except PermissionError as error:
        permission_error = ConfigFilePermissionError(f"Cannot read `{file_path}`.")
        permission_error.filename = str(file_path)
        raise permission_error from error
    # PyYAML and OmegaConf raise assorted builtin errors for invalid content
    except Exception as error:
        # A failing disk or a file that vanished is no mistake in the content. For a
        # file that holds a single number, OmegaConf raises an `OSError` without an
        # error number.
        if isinstance(error, OSError) and error.errno is not None:
            raise
        raise ConfigFileSyntaxError(
            f"Cannot parse `{file_path}`: {describe_error(error)}"
        ) from error
