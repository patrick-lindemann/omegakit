from pathlib import Path

from omegaconf import OmegaConf

from omegakit import load_config

path = Path(__file__).parent / "app.yaml"

# Dotlist strings, as they come from a command line.
config = load_config(path, overrides=["seed=42", "trainer.optimizer.lr=0.01"])
assert config.seed == 42
assert config.trainer.optimizer.lr == 0.01

# A nested dict or a DictConfig merges the same way.
config = load_config(path, overrides={"trainer": {"epochs": 3}})
assert config.trainer.epochs == 3
assert config.trainer.optimizer.name == "adam"

config = load_config(path, overrides=OmegaConf.create({"trainer": {"epochs": 5}}))
assert config.trainer.epochs == 5

# Overrides arrive after assembly, so `~import` in an override stays a string.
config = load_config(path, overrides=["seed=~import other.yaml"])
assert config.seed == "~import other.yaml"
