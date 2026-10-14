from typing import Any, overload

from omegaconf import Container, DictConfig, ListConfig, OmegaConf, TupleConfig

type Config = DictConfig | ListConfig | TupleConfig


@overload
def cast_config(config: DictConfig | dict[Any, Any]) -> DictConfig: ...


@overload
def cast_config(config: ListConfig | list[Any]) -> ListConfig: ...


@overload
def cast_config(config: TupleConfig | tuple[Any, ...]) -> TupleConfig: ...


def cast_config(
    config: Config | dict[Any, Any] | list[Any] | tuple[Any, ...],
) -> Config:
    if isinstance(config, Container):
        return config  # ty: ignore[invalid-return-type]
    return OmegaConf.create(config)
