from pathlib import Path

from omegaconf import OmegaConf

from omegakit import load_config

configs = Path(__file__).parents[2] / "webapp" / "configs"

config = load_config(configs / "envs" / "prod.yaml", keep_targets=False)
print(OmegaConf.to_container(config.server))
print(OmegaConf.to_container(config.replica))
