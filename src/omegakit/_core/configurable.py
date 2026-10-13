from typing import Any, ClassVar, Self


class Configurable:
    """__summary__"""

    schema: ClassVar[type | None] = None

    @classmethod
    def from_config(cls, config: Any, **kwargs: Any) -> Self:
        return cls(**{**config, **kwargs})
