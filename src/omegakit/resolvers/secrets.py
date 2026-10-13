from omegaconf import OmegaConf


def register_secret_resolver(*, replace: bool = False, use_cache: bool = True) -> None:
    """__summary__"""
    OmegaConf.register_resolver(
        "secret", lambda value: value, replace=replace, use_cache=use_cache
    )
