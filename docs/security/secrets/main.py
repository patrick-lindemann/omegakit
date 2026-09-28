import os
from pathlib import Path

from omegaconf import OmegaConf

from omegakit import load_config
from omegakit.resolvers.secrets import register_secret_resolver

os.environ["TRACKER_TOKEN"] = "tok-5f3a9c1e7b2d4f60"
register_secret_resolver()

config = load_config(Path(__file__).parent / "tracked.yaml")
print(OmegaConf.to_yaml(config), end="")
print(config.tracking.url.endswith("token=tok-5f3a9c1e7b2d4f60"))
