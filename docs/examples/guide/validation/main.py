from pathlib import Path

from webapp import App

from omegakit import ConfigValidationError, load_config, validate

configs = Path(__file__).parents[2] / "webapp" / "configs"

validate(load_config(configs / "app.yaml"), schema=App)

for override in ["server.workers=many", "database.$class=webapp.cache.RedisCache"]:
    config = load_config(configs / "app.yaml", overrides=[override])
    try:
        validate(config, schema=App)
    except ConfigValidationError as error:
        print(error)

base = load_config(configs / "base.yaml")
validate(base, schema=App, allow_missing=True)
