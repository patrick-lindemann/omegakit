from omegakit.utils import read_secret, register_resolver


def register_secret_resolver(*, replace: bool = False) -> None:
    """Register `${secret:NAME}`, which gives the environment variable `NAME`.

    It reads the variable when the value is resolved, as `${oc.env:NAME}` does, but
    has no default. `omegakit show --resolve` prints every value it gave as `***`.
    Registration is global to OmegaConf.

    Args:
        replace: Replace a resolver named `secret`. Defaults to `False`.
    """
    register_resolver("secret", read_secret, replace=replace)
