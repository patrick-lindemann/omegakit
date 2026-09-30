from typing import Any

from omegaconf import OmegaConf


def register_secret_resolver(*, replace: bool = False) -> None:
    """Register `${secret:...}`, which gives the value that it wraps unchanged.

    Args:
        replace: Replace a resolver named `secret`. Defaults to `False`.

    Raises:
        ValueError: If a resolver named `secret` exists and `replace` is `False`.
    """  # noqa: DOC502
    OmegaConf.register_resolver(
        "secret", _resolve_secret, replace=replace, use_cache=True
    )


def _resolve_secret(value: Any) -> Any:
    return value
