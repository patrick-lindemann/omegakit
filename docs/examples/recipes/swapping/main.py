from pathlib import Path

from webapp import App

from omegakit import ConfigValidationError, instantiate, load_config

configs = Path(__file__).parents[2] / "webapp" / "configs"
in_memory = {"database": {"$class": "webapp.db.SQLite", "url": "sqlite://"}}

app = instantiate(load_config(configs / "app.yaml", overrides=in_memory), App)
print(type(app.database).__name__, app.database.url)

try:
    config = load_config(
        configs / "app.yaml", overrides=["database.$class=webapp.cache.RedisCache"]
    )
    instantiate(config, App)
except ConfigValidationError as error:
    print(error)
