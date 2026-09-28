from pathlib import Path

from omegakit import ConfigLoadError, load_config

here = Path(__file__).parent

config = load_config(here / "experiment.yaml")
print(config.model)

config = load_config(here / "experiment.yaml", import_root=here)
print(config.model.hidden)
try:
    load_config(here / "experiments" / "large.yaml", import_root=here / "experiments")
except ConfigLoadError as error:
    print(str(error).replace(str(here), "..."))
