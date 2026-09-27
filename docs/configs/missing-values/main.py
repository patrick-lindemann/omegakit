from pathlib import Path

from omegakit import ConfigValidationError, load_config, validate

configs = Path(__file__).parents[2] / "webapp" / "configs"

base = load_config(configs / "base.yaml")
try:
    validate(base)
except ConfigValidationError as error:
    print(error)
validate(base, allow_missing=True)
