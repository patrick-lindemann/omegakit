from pathlib import Path

from omegakit import ConfigValidationError, load_config, validate

configs = Path(__file__).parents[2] / "webapp" / "configs"

config = load_config(configs / "envs" / "dev.yaml")
print(config.cache.url)
config = load_config(configs / "envs" / "dev.yaml", overrides=["server.host=10.0.0.5"])
print(config.cache.url)

base = load_config(configs / "base.yaml")
try:
    validate(base)
except ConfigValidationError as error:
    print(error)
validate(base, allow_missing=True)
