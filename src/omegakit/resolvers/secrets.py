from typing import Any

from omegakit.resolvers import register_resolver


def register_secret_resolver(*, replace: bool = False) -> None:
    """Register `${secret:...}`, which gives the value that it wraps unchanged.

    Args:
        replace: Replace a resolver named `secret`. Defaults to `False`.

    Raises:
        ValueError: If a resolver named `secret` exists and `replace` is `False`.
    """  # noqa: DOC502
    register_resolver("secret", _secret, replace=replace)


def _secret(value: Any) -> Any:
    return value
