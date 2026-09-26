from pathlib import Path

from omegaconf import OmegaConf
from omegaconf.errors import MissingMandatoryValue

from omegakit import load_config

config = load_config(Path(__file__).parent / "app.yaml")

# Interpolations resolve against the assembled config, at the node's final position.
assert config.primary.url == "postgres://db.internal:5432/orders"

# The replica's host is still `???`: loading works, access fails.
assert OmegaConf.is_missing(config.replica, "host")
try:
    config.replica.host  # noqa: B018
except MissingMandatoryValue as error:
    assert "replica.host" in str(error)
else:
    raise AssertionError("a missing value must fail on access")

# An override fills the slot.
config = load_config(
    Path(__file__).parent / "app.yaml", overrides=["replica.host=db-replica.internal"]
)
assert config.replica.url == "postgres://db-replica.internal:5432/orders"
