from typing import Any, overload

from omegaconf import Container, DictConfig, ListConfig, OmegaConf, TupleConfig

type Config = DictConfig | ListConfig | TupleConfig
"""A config node that holds other nodes: a mapping, a list or a tuple."""


@overload
def cast_config(config: DictConfig | dict[Any, Any]) -> DictConfig: ...


@overload
def cast_config(config: ListConfig | list[Any]) -> ListConfig: ...


@overload
def cast_config(config: TupleConfig | tuple[Any, ...]) -> TupleConfig: ...


def cast_config(
    config: Config | dict[Any, Any] | list[Any] | tuple[Any, ...],
) -> Config:
    """Make a config of a `dict`, `list` or `tuple`.

    Args:
        config: The value, or a config.

    Returns:
        `config` itself if it is a config, else a new copy of it.
    """
    if isinstance(config, Container):
        return config  # ty: ignore[invalid-return-type]
    return OmegaConf.create(config)
