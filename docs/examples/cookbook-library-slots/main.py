from pathlib import Path

from omegaconf import OmegaConf

from omegakit import is_valid, load_config

path = Path(__file__).parent / "app.yaml"
config = load_config(path)

assert config.api.image == "registry.example.com/api:1.4"
assert config.api.resources.cpu == 1

# The worker left a slot open; `is_valid` reports it before anything uses it.
assert OmegaConf.is_missing(config.worker.resources, "memory_gb")
assert not is_valid(config)

config = load_config(path, overrides=["worker.resources.memory_gb=2"])
assert is_valid(config)
