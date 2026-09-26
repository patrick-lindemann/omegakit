from pathlib import Path

from omegakit import load_config

config = load_config(Path(__file__).parent / "app.yaml")

# Later bases win over earlier ones, and the node's own keys win over all bases.
assert dict(config.short_run) == {"optimizer": "adam", "lr": 0.005, "epochs": 2}
assert dict(config.long_run) == {"optimizer": "adam", "lr": 0.001, "epochs": 100}
