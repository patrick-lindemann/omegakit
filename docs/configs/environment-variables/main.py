import os
from pathlib import Path

from omegakit import ConfigValidationError, load_config, validate

config = load_config(Path(__file__).parent / "tracked.yaml")
try:
    validate(config)
except ConfigValidationError as error:
    print(error)

os.environ["TRACKER_TOKEN"] = "tok-5f3a9c1e7b2d4f60"
print(config.tracker.url)
