from typing import Any, ClassVar, Self


class Configurable:
    """A class that a config builds through `from_config`, checked by its `schema`."""

    schema: ClassVar[type | None] = None
    """The `TypedDict` that checks the keys of the config, or `None`."""

    @classmethod
    def from_config(cls, config: Any, **kwargs: Any) -> Self:
        """Make an instance from the arguments that a config gives.

        The arguments of the config are built and checked against `schema`. The keyword
        arguments, such as those given when a partial is called, win over them.

        Args:
            config: The arguments of the config.
            **kwargs: Further arguments.

        Returns:
            The instance.
        """
        return cls(**{**config, **kwargs})
