import itertools
from pathlib import Path

from omegakit import load_config

path = Path(__file__).parent / "experiment.yaml"
grid = {"optimizer.lr": [0.1, 0.01], "batch_size": [32, 64]}

runs = []
for values in itertools.product(*grid.values()):
    overrides = [f"{key}={value}" for key, value in zip(grid, values, strict=True)]
    runs.append(load_config(path, overrides=overrides))

assert [run.run_name for run in runs] == [
    "baseline-lr0.1-bs32",
    "baseline-lr0.1-bs64",
    "baseline-lr0.01-bs32",
    "baseline-lr0.01-bs64",
]
# Every run is an independent config; untouched values keep their defaults.
assert all(run.optimizer.momentum == 0.9 for run in runs)
