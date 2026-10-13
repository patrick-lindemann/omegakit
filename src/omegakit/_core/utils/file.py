import os
from pathlib import Path

from omegaconf import DictConfig, ListConfig, OmegaConf

from omegakit._core.errors import (
    ConfigFileNotFoundError,
    ConfigFilePermissionError,
    ConfigFileSyntaxError,
)

from .describe import describe_error


def load_yaml(file_path: Path) -> DictConfig | ListConfig:
    if not os.path.isfile(file_path):
        raise ConfigFileNotFoundError(f"`{file_path}` is not a file.")
    try:
        return OmegaConf.load(file_path)
    except PermissionError as error:
        raise ConfigFilePermissionError(f"Cannot read `{file_path}`.") from error
    # A failing disk or a file that vanished is no mistake in the content
    except OSError:
        raise
    # PyYAML and OmegaConf raise assorted builtin errors for invalid content
    except Exception as error:
        raise ConfigFileSyntaxError(
            f"Cannot parse `{file_path}`: {describe_error(error)}"
        ) from error
