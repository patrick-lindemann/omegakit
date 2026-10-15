from omegaconf import DictConfig, ListConfig

from omegakit import apply_overrides


def check_overrides(dict_config: DictConfig, list_config: ListConfig) -> None:
    apply_overrides(dict_config, {"a": 1})
    apply_overrides(dict_config, dict_config)
    apply_overrides(dict_config, ["a=1"])
    apply_overrides(list_config, [1, "a"])
    apply_overrides(list_config, list_config)
    apply_overrides(dict_config, list_config)  # ty: ignore[no-matching-overload]
    apply_overrides(list_config, {"a": 1})  # ty: ignore[no-matching-overload]
    apply_overrides(dict_config, "a=1")  # ty: ignore[no-matching-overload]
    apply_overrides(dict_config, None)  # ty: ignore[no-matching-overload]
