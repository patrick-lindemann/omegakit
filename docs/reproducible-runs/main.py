import hashlib
import json

from omegaconf import OmegaConf
from project import CONFIGS

from omegakit import load_config

config = load_config(CONFIGS / "experiments/mlp.yaml", overrides=["model.hidden=64"])
resolved = OmegaConf.to_container(config, resolve=True)
digest = hashlib.sha256(json.dumps(resolved, sort_keys=True).encode()).hexdigest()
print("run name:", digest[:12])
