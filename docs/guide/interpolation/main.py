from pathlib import Path

from omegakit import load_config

config = load_config(Path(__file__).parent / "experiment.yaml")
print(config.run_dir, config.data.train.seed, config.data.test.n)

config.seed = 7
print(config.run_dir, config.data.train.seed)
