import os
from pathlib import Path

from omegakit import CLASS_KEY, load_config

configs = Path(__file__).parents[2] / "webapp" / "configs"

os.environ["APP_ENV"] = "prod"
os.environ["SECRET_KEY"] = "s3cr3t-from-the-vault"
config = load_config(configs / "app.yaml")
print(config.database[CLASS_KEY])
print(config.server.secret_key)
