from pathlib import Path

import yaml
from omegaconf import DictConfig, ListConfig, OmegaConf
from omegaconf.errors import OmegaConfBaseException

from .errors import ConfigLoadError, OmegaKitBaseException
from .utils import describe_error

_NULL_TAG = "tag:yaml.org,2002:null"


def load_yaml(file_path: Path) -> DictConfig | ListConfig:
    """Load one YAML file.

    Args:
        file_path: The file to load.

    Returns:
        The file's content.

    Raises:
        ConfigLoadError: If the file is not valid YAML or not UTF-8, holds a
            single value instead of a mapping or a list, or holds a value that
            OmegaConf rejects.
        OSError: If the file cannot be read.
    """  # noqa: DOC503
    try:
        # `OmegaConf.load` turns a single string into a mapping and fails on other
        # single values with an `OSError`, so look at the document first.
        document = yaml.compose(file_path.read_text("utf-8"), Loader=yaml.SafeLoader)
        if isinstance(document, yaml.ScalarNode) and document.tag != _NULL_TAG:
            raise ConfigLoadError(
                f"Cannot load `{file_path}`: it holds a single value, not a mapping "
                "or a list."
            )
        return OmegaConf.load(file_path)
    except OmegaKitBaseException:
        raise
    except (yaml.YAMLError, UnicodeDecodeError, OmegaConfBaseException) as error:
        raise ConfigLoadError(
            f"Cannot load `{file_path}`: {describe_error(error)}"
        ) from error
