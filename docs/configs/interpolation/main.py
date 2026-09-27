from pathlib import Path

from omegakit import load_config

configs = Path(__file__).parents[2] / "webapp" / "configs"

config = load_config(configs / "envs" / "dev.yaml")
print(config.cache.url)
config = load_config(configs / "envs" / "dev.yaml", overrides=["server.host=10.0.0.5"])
print(config.cache.url)
