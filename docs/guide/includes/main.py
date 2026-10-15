from omegakit import load_config

config = load_config("experiment.yaml")
print("config.model:", config.model)

import os

from omegakit import IncludeRootError

config = load_config("experiment.yaml", include_root=".")
print("config.model.hidden:", config.model.hidden)
try:
    load_config("experiments/large.yaml", include_root="experiments")
except IncludeRootError as error:
    print("error:", str(error).replace(os.getcwd(), "..."))
