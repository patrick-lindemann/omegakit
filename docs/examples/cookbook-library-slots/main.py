from pathlib import Path

from omegaconf import OmegaConf

from omegakit import ConfigValidationError, load_config, validate

path = Path(__file__).parent / "app.yaml"
config = load_config(path)

assert config.api.image == "registry.example.com/api:1.4"
assert config.api.resources.cpu == 1

# The worker left a slot open; `validate` reports it before anything uses it.
assert OmegaConf.is_missing(config.worker.resources, "memory_gb")
try:
    validate(config)
except ConfigValidationError as error:
    assert "memory_gb" in str(error)
else:
    raise AssertionError("an open slot must fail")

config = load_config(path, overrides=["worker.resources.memory_gb=2"])
validate(config)
