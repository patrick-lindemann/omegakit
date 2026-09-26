from pathlib import Path

from models import Encoder

from omegakit import ConfigValidationError, instantiate, is_valid, load_config, validate

here = Path(__file__).parent

config = load_config(here / "app.yaml")
validate(config)
assert instantiate(config.encoder, Encoder).layers == 4

# A mistake is reported with its key before anything is built. `instantiate` runs
# the same check first; its paths start at the node it builds.
config = load_config(here / "app.yaml", overrides=["encoder.width=wide"])
assert not is_valid(config)
try:
    instantiate(config.encoder)
except ConfigValidationError as error:
    assert "`width`" in str(error)
else:
    raise AssertionError("an invalid width must fail")

# The fragment alone has an open slot and refers to a key its consumer defines.
fragment = load_config(here / "encoder.yaml")
assert not is_valid(fragment)
validate(fragment, schema=Encoder, allow_missing=True)
