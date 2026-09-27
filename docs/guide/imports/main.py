from pathlib import Path

from omegakit import ConfigValidationError, load_config

here = Path(__file__).parent
configs = here.parents[1] / "webapp" / "configs"

config = load_config(configs / "app.yaml", import_root=configs)
print(list(config.jobs))

try:
    load_config(here / "shared.yaml", import_root=here)
except ConfigValidationError as error:
    print(error)
