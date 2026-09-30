from typing import Any

META_KEY = "$meta"
"""Metadata attached to a node."""


def drop_meta(value: Any) -> Any:
    """Remove `$meta` from every mapping of a resolved config.

    Args:
        value: The resolved config, as `dict`s and `list`s.

    Returns:
        `value` without `$meta`, with its containers copied.
    """
    if isinstance(value, dict):
        return {key: drop_meta(item) for key, item in value.items() if key != META_KEY}
    if isinstance(value, list):
        return [drop_meta(item) for item in value]
    return value
