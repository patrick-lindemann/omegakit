from pathlib import Path

from omegakit import REF_KEY, ConfigLoadError, load_config

here = Path(__file__).parent
configs = here.parents[1] / "curvefit" / "configs"

config = load_config(here / "cubic.yaml")
print(config.data.train.function[REF_KEY], config.data.train.noise)

config = load_config(configs / "experiments" / "poly3-adam.yaml", import_root=configs)
print(list(config.data))
try:
    load_config(here / "cubic.yaml", import_root=here)
except ConfigLoadError as error:
    print(error)
