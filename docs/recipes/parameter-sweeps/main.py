import itertools
from pathlib import Path

from webapp import App

from omegakit import instantiate, load_config

configs = Path(__file__).parents[2] / "webapp" / "configs"
grid = {"server.workers": [1, 4], "database.pool_size": [5, 20]}

for values in itertools.product(*grid.values()):
    overrides = [f"{key}={value}" for key, value in zip(grid, values, strict=True)]
    overrides.append("log_dir=runs/w${server.workers}-p${database.pool_size}")
    app = instantiate(
        load_config(configs / "app.yaml", overrides=overrides), schema=App
    )
    print(app.server.workers, app.database.pool_size, app.log_dir)
