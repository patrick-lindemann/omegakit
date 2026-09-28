import os
from pathlib import Path

from omegakit import load_config

here = Path(__file__).parent

config = load_config(here / "array.yaml")
print(config.seed, config.run_dir)

os.environ["SLURM_ARRAY_TASK_ID"] = "3"
config = load_config(here / "array.yaml")
print(repr(config.seed), config.run_dir)
