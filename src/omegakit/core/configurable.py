import dataclasses
from collections.abc import Mapping
from typing import Any, ClassVar, Self, cast

from .errors import SchemaDefinitionError
from .schema import Schema


class Configurable:
    """A class that a config builds through `from_config`."""

    __module__ = "omegakit"

    schema: ClassVar[Schema | None] = None
    """The dataclass that the class's config is checked against, or `None`."""

    @classmethod
    def from_config(cls, config: Any, **kwargs: Any) -> Self:
        """Create an instance from its config.

        Args:
            config: An instance of `schema` with its object fields built, or the
                built arguments as a mapping when the class has no schema.
            **kwargs: Call-time arguments from a partial, or extra arguments from a
                direct caller.

        Returns:
            The created instance.
        """
        if dataclasses.is_dataclass(config):
            fields = {
                field.name: getattr(config, field.name)
                for field in dataclasses.fields(config)
                if field.init
            }
        else:
            fields = dict(cast(Mapping[str, Any], config))
        return cls(**{**fields, **kwargs})


def find_schema(cls: type) -> Schema | None:
    """Find the schema of a class.

    Args:
        cls: The class.

    Returns:
        The `schema` of a `Configurable`, `cls` itself if it is a dataclass, and
        otherwise `None`.

    Raises:
        SchemaDefinitionError: If the `schema` of a `Configurable` is not a
            dataclass.
    """
    if not issubclass(cls, Configurable):
        return cls if dataclasses.is_dataclass(cls) else None
    if cls.schema is not None and not dataclasses.is_dataclass(cls.schema):
        raise SchemaDefinitionError(
            f"`{cls.__qualname__}.schema` is `{cls.schema!r}`, which is not a "
            "dataclass."
        )
    return cls.schema
