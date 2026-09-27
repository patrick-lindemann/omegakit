import os
from pathlib import Path

from omegaconf import OmegaConf

from omegakit import load_config, mask_secrets

configs = Path(__file__).parents[1] / "webapp" / "configs"
os.environ["APP_ENV"] = "prod"
os.environ["SECRET_KEY"] = "s3cr3t-from-the-vault"

config = load_config(configs / "app.yaml")
print(config.server.secret_key)
print(OmegaConf.to_yaml(mask_secrets(config)["server"]), end="")
