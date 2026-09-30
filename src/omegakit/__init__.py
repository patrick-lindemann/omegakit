from importlib.metadata import version

from .core import *  # noqa: F403
from .core import __all__ as __all__

__version__ = version("omegakit")
