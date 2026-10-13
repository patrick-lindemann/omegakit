import os
from pathlib import Path

from omegaconf import DictConfig, ListConfig, OmegaConf

from omegakit._utils.describe import describe_error

from .error import OmegaKitBaseException


class ConfigFileNotFoundError(OmegaKitBaseException, FileNotFoundError):
    pass


class ConfigFilePermissionError(OmegaKitBaseException, PermissionError):
    pass


class ConfigSyntaxError(OmegaKitBaseException, ValueError):
    pass


def load_yaml(file_path: Path) -> DictConfig | ListConfig:
    if not os.path.isfile(file_path):
        raise ConfigFileNotFoundError(f"`{file_path}` is not a file.")
    try:
        return OmegaConf.load(file_path)
    except PermissionError as error:
        raise ConfigFilePermissionError(f"Cannot read `{file_path}`.") from error
    # PyYAML and OmegaConf raise assorted builtin errors for invalid content
    except Exception as error:
        raise ConfigSyntaxError(
            f"Cannot parse `{file_path}`: {describe_error(error)}"
        ) from error
