import os
from pathlib import Path

from webapp import App

from omegakit import instantiate, load_config, validate

configs = Path(__file__).parents[2] / "webapp" / "configs"
os.environ["SECRET_KEY"] = "change-me-in-production"

for environment in ["dev", "prod"]:
    os.environ["APP_ENV"] = environment
    app = instantiate(load_config(configs / "app.yaml"), App)
    print(environment, type(app.database).__name__, app.server.workers)

validate(load_config(configs / "base.yaml"), schema=App, allow_missing=True)
