import os
from pathlib import Path

from omegakit import load_config

here = Path(__file__).parent

config = load_config(here / "experiment.yaml")
print(config.data_dir, repr(config.seed))

os.environ["DATA_DIR"] = "/datasets/sine"
os.environ["SLURM_ARRAY_TASK_ID"] = "3"
print(config.data_dir, repr(config.seed))
