from pathlib import Path

from omegakit import load_config

experiments = Path(__file__).parents[2] / "curvefit" / "configs" / "experiments"

config = load_config(experiments / "poly3-adam.yaml")
print(config.tracker.run_dir, config.data.train.seed)
config = load_config(experiments / "poly3-adam.yaml", overrides=["seed=7"])
print(config.tracker.run_dir, config.data.train.seed)
