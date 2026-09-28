import os

from omegakit import load_config

config = load_config("experiment.yaml")
print("config.data_dir:", config.data_dir)
print("config.seed:", config.seed)

os.environ["DATA_DIR"] = "/datasets/sine"
os.environ["SLURM_ARRAY_TASK_ID"] = "3"
print("config.data_dir:", config.data_dir)
print("config.seed:", config.seed)
print("type(config.seed):", type(config.seed).__name__)
