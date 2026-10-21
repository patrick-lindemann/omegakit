from typing import Any, ClassVar

from typing_extensions import Self, is_typeddict

from omegakit._core.errors import SchemaDefinitionError

# The default of the `schema` keyword, which keeps the schema of the parent class
_INHERITED: Any = object()


class Configurable:
    """A class that a config builds through `from_config`, checked by its schema.

    A subclass names its schema in the class keyword `schema`, as in
    `class Model(Configurable, schema=ModelConfig)`. A keyword, unlike a class
    attribute, is checked by type checkers, and a misspelled one raises when the class
    is defined.
    """

    _schema: ClassVar[type | None] = None

    def __init_subclass__(cls, *, schema: type | None = _INHERITED) -> None:
        """Set the schema of a subclass.

        Args:
            schema: The `TypedDict` that checks the keys of the config, or `None` for
                none. Defaults to the schema of the parent class.

        Raises:
            SchemaDefinitionError: If `schema` is neither a `TypedDict` nor `None`.
        """
        super().__init_subclass__()
        if schema is _INHERITED:
            return
        if schema is not None and not is_typeddict(schema):
            raise SchemaDefinitionError(
                f"The schema of `{cls.__qualname__}` must be a `TypedDict`, "
                f"not `{schema!r}`."
            )
        cls._schema = schema

    @classmethod
    def from_config(cls, config: Any, **kwargs: Any) -> Self:
        """Make an instance from the arguments that a config gives.

        The arguments of the config are built and checked against the schema. The
        keyword arguments, such as those given when a partial is called, win over them.

        Args:
            config: The arguments of the config.
            **kwargs: Further arguments.

        Returns:
            The instance.
        """
        return cls(**{**config, **kwargs})
