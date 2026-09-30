import dataclasses
from typing import Any, ClassVar, Protocol


# Dataclasses share no base class. This is typeshed's `DataclassInstance`, which
# exists only for type checkers.
class _DataclassInstance(Protocol):
    __dataclass_fields__: ClassVar[dict[str, dataclasses.Field[Any]]]


type Schema = type[_DataclassInstance]
"""A class that declares the fields of a config node: a dataclass."""
