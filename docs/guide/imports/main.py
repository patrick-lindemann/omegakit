import os

from omegakit import ConfigLoadError, load_config

config = load_config("experiment.yaml")
print("config.model:", config.model)

config = load_config("experiment.yaml", import_root=".")
print("config.model.hidden:", config.model.hidden)
try:
    load_config("experiments/large.yaml", import_root="experiments")
except ConfigLoadError as error:
    print("error:", str(error).replace(os.getcwd(), "..."))
