import dataclasses
from collections.abc import Mapping
from typing import Any, Generic, Self, cast

from typing_extensions import TypeVar

TConfig = TypeVar("TConfig", default=Mapping[str, Any])


class Configurable(Generic[TConfig]):
    """A class that can be instantiated from a config."""

    @classmethod
    def from_config(cls, config: TConfig, **kwargs: Any) -> Self:
        """Create an instance from a validated config.

        Args:
            config: The typed config, an instance of the dataclass `TConfig` with its
                object fields built, or the materialized arguments as a mapping when
                the class has no dataclass schema.
            **kwargs: Call-time arguments from a partial, or extra arguments from a
                direct caller. They win over config fields of the same name.

        Returns:
            The created instance.
        """
        if dataclasses.is_dataclass(config):
            fields = {
                field.name: getattr(config, field.name)
                for field in dataclasses.fields(config)
            }
        else:
            fields = dict(cast(Mapping[str, Any], config))
        return cls(**{**fields, **kwargs})
