from pathlib import Path

from omegaconf import OmegaConf
from omegaconf.errors import MissingMandatoryValue

from omegakit import load_config

config = load_config(Path(__file__).parent / "experiment.yaml")
print(OmegaConf.missing_keys(config))
try:
    print(config.name)
except MissingMandatoryValue as error:
    print(str(error).splitlines()[0])

config.name = "wide"
print(OmegaConf.missing_keys(config), config.name)
