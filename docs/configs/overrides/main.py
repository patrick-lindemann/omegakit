from pathlib import Path

from omegakit import load_config

configs = Path(__file__).parents[2] / "webapp" / "configs"

config = load_config(
    configs / "app.yaml", overrides=["server.port=9000", "server.workers=4"]
)
print(config.server.port, config.server.workers)

config = load_config(configs / "app.yaml", overrides={"database": {"pool_size": 1}})
print(config.database.pool_size)
