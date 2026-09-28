from pathlib import Path

from omegakit import load_config

config = load_config(Path(__file__).parent / "experiment.yaml")
print("type(config):", type(config).__name__)
print("config.model.hidden:", config.model.hidden)
print("config.optimizer.lr:", config.optimizer.lr)
