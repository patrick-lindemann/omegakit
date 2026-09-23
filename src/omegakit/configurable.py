from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Generic

from omegaconf import DictConfig
from typing_extensions import TypeVar

TConfig = TypeVar("TConfig", bound=Mapping[str, Any], default=DictConfig)


class Configurable(Generic[TConfig]):
    """A class that can be instantiated from a config."""

    @classmethod
    def from_config(
        cls, config: TConfig | DictConfig | dict[str, Any], **kwargs
    ) -> Any:
        """Create an instance from a materialized config.

        Args:
            config: The constructor arguments, keyed by parameter name.
            **kwargs: Call-time arguments from a partial. They win over `config`
                arguments of the same name.

        Returns:
            The created instance.
        """
        return cls(**dict(config, **kwargs))
