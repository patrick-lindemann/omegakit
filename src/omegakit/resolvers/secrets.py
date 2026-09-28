import os

from omegakit.registry import register_resolver


def register_secret_resolver(*, replace: bool = False) -> None:
    """Register `${secret:NAME}`, which gives the environment variable `NAME`.

    Args:
        replace: Replace a resolver named `secret`. Defaults to `False`.

    Raises:
        ValueError: If a resolver named `secret` exists and `replace` is `False`.
    """  # noqa: DOC502
    register_resolver("secret", _read_secret, replace=replace)


def _read_secret(name: str) -> str:
    try:
        return os.environ[name]
    except KeyError:
        raise ValueError(f"Environment variable `{name}` is not set.") from None
