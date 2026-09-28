from omegakit.registry import read_secret, register_resolver


def register_secret_resolver(*, replace: bool = False) -> None:
    """Register `${secret:NAME}`, which gives the environment variable `NAME`.

    Args:
        replace: Replace a resolver named `secret`. Defaults to `False`.
    """
    register_resolver("secret", read_secret, replace=replace)
