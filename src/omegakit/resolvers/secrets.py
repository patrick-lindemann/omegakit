from omegaconf import OmegaConf


def register_secret_resolver(*, replace: bool = False, use_cache: bool = True) -> None:
    """Register `${secret:value}`, which resolves to `value` and marks it as a secret.

    Args:
        replace: Whether to replace a registered resolver of the same name. Defaults
            to `False`.
        use_cache: Whether to cache each result by its arguments. Defaults to `True`.
    """
    OmegaConf.register_resolver(
        "secret", lambda value: value, replace=replace, use_cache=use_cache
    )
