from omegaconf import OmegaConf
from omegaconf.errors import MissingMandatoryValue

from omegakit import load_config

config = load_config("experiment.yaml")
print("missing keys:", OmegaConf.missing_keys(config))
try:
    print("config.name:", config.name)
except MissingMandatoryValue as error:
    print("error:", str(error).splitlines()[0])

config.name = "wide"
print("missing keys:", OmegaConf.missing_keys(config))
print("config.name:", config.name)
