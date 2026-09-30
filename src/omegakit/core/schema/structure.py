import dataclasses
import functools
from typing import Any

from .field import classify_fields
from .schema import Schema


@functools.cache
def derive_structure(schema: Schema) -> type:
    """Derive the dataclass that OmegaConf checks a node of a schema with.

    Args:
        schema: The schema to derive the structure from.

    Returns:
        A dataclass of the same name with the configurable fields of `schema`. A
        data field keeps its annotation and default. Any other field holds `Any`,
        with `None` as its default where the field has a default.
    """
    fields = classify_fields(schema)
    structure = []
    for field in dataclasses.fields(schema):
        if field.name not in fields:
            continue
        kind, annotation = fields[field.name]
        if kind == "data":
            default = dataclasses.field(
                default=field.default, default_factory=field.default_factory
            )
        elif (
            field.default is dataclasses.MISSING
            and field.default_factory is dataclasses.MISSING
        ):
            default = dataclasses.field()
        else:
            default = dataclasses.field(default=None)
        structure.append((field.name, annotation if kind == "data" else Any, default))
    return dataclasses.make_dataclass(schema.__name__, structure, kw_only=True)
