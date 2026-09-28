from pathlib import Path

from omegakit import load_config

config = load_config(Path(__file__).parent / "experiment.yaml")
for name, split in config.data.items():
    print(name, split.n, split.noise, split.seed)
