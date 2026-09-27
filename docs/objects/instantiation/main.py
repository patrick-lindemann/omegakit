from pathlib import Path

from webapp import App
from webapp.db import Database

from omegakit import ConfigValidationError, instantiate, load_config, prepare

configs = Path(__file__).parents[2] / "webapp" / "configs"
config = load_config(configs / "app.yaml")

app = instantiate(config, schema=App)
print(type(app.database).__name__, type(app.jobs["digest"]).__name__)
print(app.jobs["cleanup"].handler())
print(app.jobs["digest"].handler())
print(app.jobs["digest"].handler(subject="Special offer"))

make_database = prepare(config.database, schema=Database)
print(make_database(pool_size=1).pool_size)

try:
    instantiate(
        config,
        schema=App,
        overrides=["database.$class=subprocess.Popen"],
        allowed_modules=["webapp"],
    )
except ConfigValidationError as error:
    print(error)
