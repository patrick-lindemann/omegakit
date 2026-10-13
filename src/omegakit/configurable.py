import dataclasses
from collections.abc import Mapping
from typing import Any, ClassVar, Self, cast


class Configurable:
    """__summary__"""

    schema: ClassVar[type | None] = None

    @classmethod
    def from_config(cls, config: Any, **kwargs: Any) -> Self:
        if dataclasses.is_dataclass(config):
            fields = {
                field.name: getattr(config, field.name)
                for field in dataclasses.fields(config)
                if field.init
            }
        else:
            fields = dict(cast(Mapping[str, Any], config))
        return cls(**{**fields, **kwargs})
