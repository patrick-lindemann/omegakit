from pathlib import Path

from omegakit import load_config
from omegakit.resolvers.paths import register_paths_resolver

configs = Path(__file__).parents[2] / "webapp" / "configs"

register_paths_resolver({"logs": Path("/var/log")})
config = load_config(configs / "app.yaml", overrides=["log_dir=${paths:logs}/webapp"])
print(config.log_dir)
