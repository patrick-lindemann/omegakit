from pathlib import Path

import yaml
from omegaconf import DictConfig, ListConfig, OmegaConf
from omegaconf.errors import OmegaConfBaseException

from .errors import ConfigLoadError
from .utils import describe_error


def load_yaml(file_path: Path) -> DictConfig | ListConfig:
    """Load one YAML file with `OmegaConf.load`.

    Args:
        file_path: The file to load.

    Returns:
        The file's content.

    Raises:
        ConfigLoadError: If `OmegaConf.load` fails for any reason other than a file
            that does not exist.
        FileNotFoundError: If the file does not exist.
    """  # noqa: DOC503
    try:
        return OmegaConf.load(file_path)
    except FileNotFoundError:
        raise
    except (
        OSError,
        yaml.YAMLError,
        UnicodeDecodeError,
        OmegaConfBaseException,
    ) as error:
        raise ConfigLoadError(
            f"Cannot load `{file_path}`: {describe_error(error)}"
        ) from error
